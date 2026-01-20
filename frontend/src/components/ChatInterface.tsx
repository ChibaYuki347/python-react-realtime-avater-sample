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
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  onNewMessage,
  className = ''
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [streamingResponse, setStreamingResponse] = useState('');
  const [lastAIResponse, setLastAIResponse] = useState<string>('');
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

      const response = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId || undefined,
          max_tokens: 2000,
          temperature: 0.7
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Handle streaming response
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
              }
                
                // ストリーミング完了
                if (data.done) {
                  console.log('Streaming complete, final response:', fullResponse); // デバッグログ
                  // Final response received
                  const assistantMessage: Message = {
                    id: `assistant-${Date.now()}`,
                    role: 'assistant',
                    content: fullResponse,
                    timestamp: new Date().toISOString()
                  };
                  
                  setMessages(prev => [...prev, assistantMessage]);
                  setStreamingResponse('');
                  setLastAIResponse(fullResponse);  // 最後のAI応答を保存
                  
                  // Call onNewMessage callback if provided
                  if (onNewMessage) {
                    onNewMessage(userMessage, fullResponse);
                  }
                  break;
                }
                
                // レガシーフォーマット対応（後方互換性）
                if (data.type === 'session' && data.session_id) {
                  currentSessionId = data.session_id;
                  setSessionId(currentSessionId);
                }
                
                if (data.type === 'content' && data.content) {
                  fullResponse += data.content;
                  setStreamingResponse(fullResponse);
                }
                
                if (data.type === 'complete') {
                  // Final response received
                  const assistantMessage: Message = {
                    id: `assistant-${Date.now()}`,
                    role: 'assistant',
                    content: data.full_response || fullResponse,
                    timestamp: new Date().toISOString()
                  };
                  
                  setMessages(prev => [...prev, assistantMessage]);
                  setStreamingResponse('');
                  
                  // Call onNewMessage callback if provided
                  if (onNewMessage) {
                    onNewMessage(userMessage, data.full_response || fullResponse);
                  }
                  break;
                }
                
                if (data.type === 'error') {
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
  }, [inputMessage, isLoading, sessionId, onNewMessage]);

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
  const speakWithAvatar = useCallback(() => {
    if (lastAIResponse && onNewMessage) {
      onNewMessage('', lastAIResponse);
    }
  }, [lastAIResponse, onNewMessage]);

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
        <h3>AI アシスタント (GPT-4.1)</h3>
        <div className="chat-controls">
          {sessionId && (
            <span className="session-info">Session: {sessionId.slice(-8)}</span>
          )}
          <button 
            onClick={speakWithAvatar}
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