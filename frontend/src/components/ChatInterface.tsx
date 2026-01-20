import React, { useState, useRef } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface ChatInterfaceProps {
  speakWithAvatarFunction?: ((text: string) => Promise<void>) | null;
  onNewMessage?: (userMessage: string, assistantMessage: string) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ 
  speakWithAvatarFunction = null, 
  onNewMessage 
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [streamingResponse, setStreamingResponse] = useState('');
  const [lastAIResponse, setLastAIResponse] = useState<string>('');
  const [useRAG, setUseRAG] = useState(false);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    
    // Add user message to messages
    const newUserMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, newUserMessage]);
    setInputMessage('');
    setIsLoading(true);
    setStreamingResponse('');

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    try {
      // Choose endpoint based on RAG mode
      const endpoint = useRAG ? '/api/rag/query' : '/api/ai/chat';
      
      // Prepare request body
      const requestBody = useRAG 
        ? { query: userMessage }
        : { 
            message: userMessage,
            session_id: sessionId || null,
            streaming: true
          };

      console.log('Sending request to:', endpoint);
      console.log('Request body:', requestBody);

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // RAGレスポンスの場合は直接JSONを処理
      if (useRAG) {
        const ragResponse = await response.json();
        console.log('RAG Response received:', ragResponse);
        
        const finalResponse = ragResponse.answer || 'RAG応答の取得に失敗しました。';
        
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant', 
          content: finalResponse,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, assistantMessage]);
        setLastAIResponse(finalResponse);
        setSessionId(ragResponse.conversation_id || sessionId);
        
        // RAG応答での自動読み上げ
        if (speakWithAvatarFunction && finalResponse.trim()) {
          console.log('RAG自動アバター読み上げ開始:', finalResponse);
          try {
            await speakWithAvatarFunction(finalResponse);
          } catch (speakError) {
            console.error('RAGアバター読み上げエラー:', speakError);
          }
        }
        
        // Call onNewMessage callback
        if (onNewMessage) {
          onNewMessage(userMessage, finalResponse);
        }

        return;
      }

      // 通常のストリーミング応答の処理
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      let fullResponse = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Decode the chunk
          const chunk = new TextDecoder().decode(value);
          console.log('Raw chunk received:', chunk);
          
          try {
            // 直接JSONオブジェクトとして処理
            const data = JSON.parse(chunk.trim());
            console.log('Parsed data:', data);
            
            // バックエンドの形式に応じて処理
            if (data.response) {
              // 単一の完全な応答
              fullResponse = data.response;
              
              const assistantMessage: Message = {
                id: `assistant-${Date.now()}`,
                role: 'assistant',
                content: fullResponse,
                timestamp: new Date().toISOString()
              };
              
              setMessages(prev => [...prev, assistantMessage]);
              setLastAIResponse(fullResponse);
              setStreamingResponse('');
              setSessionId(data.session_id || sessionId);
              
              // 自動読み上げ判定
              const hasContent = fullResponse && fullResponse.trim().length > 0;
              const hasSpeakFunction = speakWithAvatarFunction !== null && speakWithAvatarFunction !== undefined;
              console.log('自動読み上げチェック:', { hasSpeakFunction, hasContent });
              
              if (hasSpeakFunction && hasContent) {
                console.log('自動アバター読み上げ開始:', fullResponse);
                try {
                  await speakWithAvatarFunction(fullResponse);
                } catch (speakError) {
                  console.error('アバター読み上げエラー:', speakError);
                }
              }
              
              // Call onNewMessage callback
              if (onNewMessage) {
                onNewMessage(userMessage, fullResponse);
              }
              
              break; // 応答完了
            }
          } catch (parseError) {
            console.warn('Failed to parse chunk as JSON:', parseError, 'Chunk:', chunk);
          }
        }
      } finally {
        reader.releaseLock();
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Request aborted');
      } else {
        console.error('Error sending message:', error);
        // Show error message to user
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `エラーが発生しました: ${error.message}`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } finally {
      setIsLoading(false);
      setStreamingResponse('');
      abortControllerRef.current = null;
    }
  };

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
      setStreamingResponse('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      sendMessage();
    }
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#f5f5f5' }}>
      {/* ヘッダー */}
      <div style={{ 
        padding: '1rem', 
        backgroundColor: 'white', 
        borderBottom: '1px solid #e0e0e0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <h2 style={{ margin: 0, color: '#333' }}>AI Chat</h2>
        
        {/* RAG設定 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.9rem', color: '#333', fontWeight: '500' }}>
            <input
              type="checkbox"
              checked={useRAG}
              onChange={(e) => setUseRAG(e.target.checked)}
              style={{ marginRight: '0.5rem' }}
            />
            RAG機能を使用
          </label>
        </div>
      </div>

      {/* メインチャットエリア */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* チャット表示エリア */}
        <div style={{ 
          flex: 1, 
          overflowY: 'auto', 
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          {messages.map((message) => (
            <div key={message.id} style={{
              display: 'flex',
              justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start'
            }}>
              <div style={{
                maxWidth: '70%',
                padding: '0.75rem 1rem',
                borderRadius: '0.5rem',
                backgroundColor: message.role === 'user' ? '#007bff' : 'white',
                color: message.role === 'user' ? 'white' : '#333',
                border: message.role === 'user' ? 'none' : '1px solid #e0e0e0',
                boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
              }}>
                <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                  {message.content}
                </div>
                <div style={{
                  fontSize: '0.75rem',
                  marginTop: '0.25rem',
                  opacity: 0.7
                }}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}

          {/* ストリーミング中の応答表示 */}
          {streamingResponse && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div style={{
                maxWidth: '70%',
                padding: '0.75rem 1rem',
                borderRadius: '0.5rem',
                backgroundColor: '#f8f9fa',
                color: '#333',
                border: '1px solid #e0e0e0',
                boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
              }}>
                <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                  {streamingResponse}
                </div>
                <div style={{
                  fontSize: '0.8rem',
                  color: '#007bff',
                  marginTop: '0.25rem'
                }}>
                  入力中...
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 入力エリア */}
        <div style={{
          borderTop: '1px solid #e0e0e0',
          backgroundColor: 'white',
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem'
        }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={useRAG ? "RAG機能でドキュメントを検索して応答します..." : "メッセージを入力してください..."}
              style={{
                flex: 1,
                padding: '0.75rem',
                border: '1px solid #ddd',
                borderRadius: '0.5rem',
                fontSize: '1rem',
                outline: 'none'
              }}
              disabled={isLoading}
            />
            {isLoading ? (
              <button
                onClick={stopGeneration}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#dc3545',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: 'pointer'
                }}
              >
                停止
              </button>
            ) : (
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim()}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: inputMessage.trim() ? '#007bff' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: inputMessage.trim() ? 'pointer' : 'not-allowed'
                }}
              >
                送信
              </button>
            )}
          </div>
          
          {/* 設定情報表示 */}
          <div style={{ fontSize: '0.8rem', color: '#333', fontWeight: '500' }}>
            モード: {useRAG ? 'RAG' : 'AI'} | 状態: {isLoading ? '処理中' : '待機中'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;