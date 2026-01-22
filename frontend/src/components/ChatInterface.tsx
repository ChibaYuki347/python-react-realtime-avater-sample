import React, { useState, useRef, useEffect } from 'react';
import { WebSpeechRecognizer, checkMicrophonePermission, isBrowserSupported, checkSpeechToTextEnvironment } from '../utils/speechToTextUtils';

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
  const [isListening, setIsListening] = useState(false);
  const [interimText, setInterimText] = useState('');
  const [microphoneSupported, setMicrophoneSupported] = useState(false);
  const [microphonePermission, setMicrophonePermission] = useState<boolean | null>(null);
  const [speechError, setSpeechError] = useState<string>('');
  
  const abortControllerRef = useRef<AbortController | null>(null);
  const speechRecognizerRef = useRef<WebSpeechRecognizer | null>(null);

  // 初期化：Speech-to-Text サポート確認とマイク権限チェック
  useEffect(() => {
    const initializeSpeechToText = async () => {
      // 環境チェック
      const envCheck = checkSpeechToTextEnvironment();
      console.log('[ChatInterface] Speech-to-Text 環境情報:', envCheck);

      if (!envCheck.isSupported) {
        setSpeechError(envCheck.message);
        setMicrophoneSupported(false);
        return;
      }

      if (!envCheck.isSecure) {
        console.warn('[ChatInterface] Web Speech API セキュリティ警告:', envCheck.message);
      }

      setMicrophoneSupported(true);

      try {
        const hasPermission = await checkMicrophonePermission();
        setMicrophonePermission(hasPermission);
        if (!hasPermission) {
          setSpeechError('マイクへのアクセス権限がありません。ブラウザの設定を確認してください。');
        }
      } catch (error) {
        console.error('[ChatInterface] マイク権限チェックエラー:', error);
        setMicrophonePermission(false);
      }
    };

    initializeSpeechToText();
  }, []);

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
      const endpoint = useRAG ? '/api/azure-rag/query' : '/api/ai/chat';
      
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

  const startListening = async () => {
    if (!microphonePermission) {
      setSpeechError('マイクへのアクセス権限がありません。ブラウザの設定を確認してください。');
      return;
    }

    try {
      setSpeechError('');
      setIsListening(true);
      setInterimText('');

      // Speech Recognizer を初期化
      if (!speechRecognizerRef.current) {
        speechRecognizerRef.current = new WebSpeechRecognizer();
      }

      const recognizer = speechRecognizerRef.current;

      // リアルタイム中間テキスト更新のため、定期的にチェック
      const updateInterval = setInterval(() => {
        setInterimText(recognizer.getInterimTranscript());
      }, 100);

      // エラーハンドラーをオーバーライド
      const originalRecognition = (recognizer as any).recognition;
      if (originalRecognition) {
        originalRecognition.onerror = (event: any) => {
          const errorMsg = recognizer.getErrorMessage(event.error);
          setSpeechError(errorMsg);
          console.error('[ChatInterface] Speech-to-Text エラー:', event.error, '-', errorMsg);
          setIsListening(false);
          clearInterval(updateInterval);
        };
      }

      // 音声認識開始
      recognizer.start();

      // マイクボタン長押し時の自動停止（15秒後）
      setTimeout(() => {
        if (isListening) {
          stopListening();
        }
      }, 15000);

      // クリーンアップ関数で interval をクリア
      return () => clearInterval(updateInterval);
    } catch (error) {
      console.error('[ChatInterface] 音声認識開始エラー:', error);
      setSpeechError('音声認識の開始に失敗しました。ブラウザの設定を確認してください。');
      setIsListening(false);
    }
  };

  const stopListening = async () => {
    if (!speechRecognizerRef.current) return;

    try {
      const recognizer = speechRecognizerRef.current;
      const finalText = await recognizer.stop();

      // 認識結果をテキストボックスに設定
      setInputMessage(finalText);
      setInterimText('');
      setIsListening(false);
      setSpeechError('');

      console.log('[ChatInterface] 音声認識完了:', finalText);
    } catch (error) {
      console.error('[ChatInterface] 音声認識停止エラー:', error);
      setSpeechError('音声認識の停止中にエラーが発生しました。');
      setIsListening(false);
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
          {/* 音声入力中の表示 */}
          {isListening && (
            <div style={{
              padding: '0.75rem',
              backgroundColor: '#fff3cd',
              border: '1px solid #ffc107',
              borderRadius: '0.5rem',
              fontSize: '0.9rem',
              color: '#856404'
            }}>
              🎤 {interimText ? `認識中: ${interimText}` : '音声入力待機中...'}
            </div>
          )}

          {/* エラーメッセージ表示 */}
          {speechError && (
            <div style={{
              padding: '0.75rem',
              backgroundColor: '#f8d7da',
              border: '1px solid #f5c6cb',
              borderRadius: '0.5rem',
              fontSize: '0.9rem',
              color: '#721c24',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>⚠️ {speechError}</span>
              <button
                onClick={() => setSpeechError('')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#721c24',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
              >
                ✕
              </button>
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              value={inputMessage || interimText}
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
              disabled={isLoading || isListening}
            />
            
            {/* 音声入力ボタン */}
            {microphoneSupported && (
              <button
                onMouseDown={startListening}
                onMouseUp={stopListening}
                onTouchStart={startListening}
                onTouchEnd={stopListening}
                title="マイクボタンを長押しして音声入力"
                style={{
                  padding: '0.75rem',
                  backgroundColor: isListening ? '#dc3545' : '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  fontSize: '1.2rem',
                  minWidth: '50px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                🎤
              </button>
            )}
            
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
                disabled={!inputMessage.trim() && !interimText.trim()}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: (inputMessage.trim() || interimText.trim()) ? '#007bff' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: (inputMessage.trim() || interimText.trim()) ? 'pointer' : 'not-allowed'
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