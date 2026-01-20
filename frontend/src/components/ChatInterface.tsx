import React, { useState, useCallback, useRef, useEffect } from 'react';
import './ChatInterface.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

interface ChatInterfaceProps {
  onNewMessage?: (message: string, response: string) => void;
  className?: string;
  speakWithAvatarFunction?: ((text: string) => Promise<void>) | null;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  onNewMessage,
  className = '',
  speakWithAvatarFunction
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [streamingResponse, setStreamingResponse] = useState('');
  const [lastAIResponse, setLastAIResponse] = useState<string>('');
  const [useRAG, setUseRAG] = useState<boolean>(false); // RAG使用オプション
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingResponse, scrollToBottom]);

  // Send message to AI
  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);
    setStreamingResponse('');

    // Add user message to chat
    const userMessageObj: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessageObj]);

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      // RAGまたは通常のAI応答を選択
      const endpoint = useRAG ? '/api/rag/query' : '/api/ai/chat/stream';
      const requestBody = useRAG 
        ? {
            user_id: 'user_001',  // TODO: 実際のユーザーIDに変更
            query: userMessage,
            conversation_id: sessionId || undefined,
            max_results: 5
          }
        : {
            message: userMessage,
            session_id: sessionId || undefined,
            max_tokens: 2000,
            temperature: 0.7
          };

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
            speakWithAvatarFunction(finalResponse);
          } catch (error) {
            console.error('RAG自動読み上げエラー:', error);
          }
        }
        
        if (onNewMessage) {
          onNewMessage(userMessage, finalResponse);
        }
        return;
      }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // ストリーミング応答の処理
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      let fullResponse = '';
      let currentSessionId = sessionId;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Decode the chunk
          const chunk = new TextDecoder().decode(value);
          console.log('Raw chunk received:', chunk); // デバッグログ
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const jsonString = line.slice(6);
                console.log('Raw JSON string:', jsonString); // デバッグログ
                const data = JSON.parse(jsonString);
                console.log('Parsed data:', data); // デバッグログ
                
                // バックエンドからのエラー応答をチェック
                if (data.error) {
                  throw new Error(data.error);
                }
                
                if (data.type === 'content') {
                  console.log('Adding content:', data.content);
                  fullResponse += data.content;
                  setStreamingResponse(fullResponse);
                  console.log('Current fullResponse:', fullResponse);
                } else if (data.type === 'complete') {
                  // ストリーミング完了 - full_responseを使用
                  const finalResponse = data.full_response || fullResponse;
                  console.log('Streaming complete, final response:', finalResponse);
                  
                  const assistantMessage: Message = {
                    id: `assistant-${Date.now()}`,
                    role: 'assistant',
                    content: finalResponse,
                    timestamp: new Date().toISOString()
                  };
                  
                  setMessages(prev => [...prev, assistantMessage]);
                  setStreamingResponse('');
                  setLastAIResponse(finalResponse);  // 最後のAI応答を保存
                  
                  // 自動でアバターに読み上げさせる
                  if (speakWithAvatarFunction && finalResponse.trim()) {
                    console.log('自動アバター読み上げ開始:', finalResponse);
                    try {
                      speakWithAvatarFunction(finalResponse);
                    } catch (error) {
                      console.error('自動読み上げエラー:', error);
                    }
                  } else {
                    console.log('自動読み上げスキップ:', {
                      hasSpeakFunction: !!speakWithAvatarFunction,
                      hasContent: !!finalResponse.trim()
                    });
                  }
                  
                  // Call onNewMessage callback if provided
                  if (onNewMessage) {
                    onNewMessage(userMessage, finalResponse);
                  }
                  break;
                } else if (data.type === 'session' && data.session_id) {
                  currentSessionId = data.session_id;
                  setSessionId(currentSessionId);
                } else if (data.type === 'error') {
                  throw new Error(data.message);
                }
              } catch (parseError) {
                console.warn('Failed to parse streaming data:', parseError);
              }
            }
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
        
        // Add error message to chat
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `申し訳ありません。エラーが発生しました: ${error.message}`,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, errorMessage]);
      }
      setStreamingResponse('');
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
      // フォーカスを戻さず、アバター領域にユーザーの注意を向ける
      if (inputRef.current) {
        inputRef.current.blur();
      }
    }
  }, [inputMessage, isLoading, sessionId, onNewMessage, speakWithAvatarFunction, useRAG]);

  // Handle Enter key press
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  // Stop streaming
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  // Clear conversation
  const clearConversation = useCallback(() => {
    setMessages([]);
    setSessionId('');
    setStreamingResponse('');
    setLastAIResponse('');
  }, []);

  // Send last AI response to avatar
  const handleSpeakWithAvatar = useCallback(() => {
    if (lastAIResponse && speakWithAvatarFunction) {
      speakWithAvatarFunction(lastAIResponse);
    }
  }, [lastAIResponse, speakWithAvatarFunction]);

  // Format timestamp
  const formatTimestamp = useCallback((timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }, []);

  return (
    <div className={`chat-interface ${className}`}>
      <div className="chat-header">
        <h3>AI アシスタント {useRAG ? '(RAG + GPT-4.1)' : '(Azure OpenAI GPT-4.1)'}</h3>
        <div className="chat-controls">
          {/* RAGオプション選択 */}
          <div className="rag-toggle">
            <label className="rag-switch">
              <input 
                type="checkbox" 
                checked={useRAG} 
                onChange={(e) => setUseRAG(e.target.checked)}
                disabled={isLoading}
              />
              <span className="rag-slider"></span>
              <span className="rag-label">RAG検索</span>
            </label>
          </div>
          
          {sessionId && (
            <span className="session-info">Session: {sessionId.slice(-8)}</span>
          )}
          <button 
            onClick={handleSpeakWithAvatar}
            className="avatar-btn"
            disabled={!lastAIResponse || isLoading}
            title="最後のAI応答をアバターで再生"
          >
            🗣️ アバター再生
          </button>
          <button 
            onClick={clearConversation}
            className="clear-btn"
            disabled={isLoading}
          >
            クリア
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="message-content">
              <div className="message-text">
                {message.content}
              </div>
              <div className="message-timestamp">
                {formatTimestamp(message.timestamp)}
              </div>
            </div>
          </div>
        ))}
        
        {/* Streaming response */}
        {streamingResponse && (
          <div className="message assistant streaming">
            <div className="message-content">
              <div className="message-text">
                {streamingResponse}
                <span className="cursor">▊</span>
              </div>
              <button 
                onClick={stopStreaming}
                className="stop-streaming-btn"
                title="応答を停止"
              >
                ⏹
              </button>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <div className="input-container">
          <textarea
            ref={inputRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="メッセージを入力してください... (Enter で送信、Shift+Enter で改行)"
            disabled={isLoading}
            rows={1}
            className="message-input"
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="send-btn"
          >
            {isLoading ? '...' : '送信'}
          </button>
        </div>
      </div>

      {messages.length === 0 && (
        <div className="chat-welcome">
          <p>GPT-4.1搭載のAIアシスタントです。</p>
          <p>質問や相談を日本語でお気軽にどうぞ！</p>
        </div>
      )}
    </div>
  );
};