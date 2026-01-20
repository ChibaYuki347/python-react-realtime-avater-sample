import React, { useState, useCallback } from 'react';
import AvatarPlayer from './components/AvatarPlayer';
import { ChatInterface } from './components/ChatInterface';
import './index.css';

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');
  const [isAIMode, setIsAIMode] = useState<boolean>(true);
  const [speakWithAvatarFunction, setSpeakWithAvatarFunction] = useState<((text: string) => Promise<void>) | null>(null);

  // アバター読み上げ関数を受け取る
  const handleSpeakWithAvatarReady = useCallback((speakFunction: (text: string) => Promise<void>) => {
    setSpeakWithAvatarFunction(() => speakFunction);
  }, []);

  // Handle AI chat response - no longer needed for auto-speak (handled in ChatInterface)
  const handleAIResponse = useCallback((userMessage: string, aiResponse: string) => {
    console.log('AI Response received:', { userMessage, aiResponse });
    
    // ChatInterfaceで自動読み上げを行うため、ここでは手動用のメッセージ設定のみ
    // コメントアウト: 自動読み上げは ChatInterface で処理
    // if (aiResponse && aiResponse.trim()) {
    //   console.log('Setting message for avatar:', aiResponse.trim());
    //   setMessage(aiResponse.trim());
    // }
  }, []);

  // Handle manual text input for avatar
  const handleManualInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setMessage(e.target.value);
  }, []);

  return (
    <div className="app">
      <div className="header">
        <h1>AI強化リアルタイムアバターシステム</h1>
        <p>GPT-4.1 + Azure Speech SDK による次世代対話型アバター体験</p>
        
        <div className="mode-toggle">
          <button 
            className={`mode-btn ${isAIMode ? 'active' : ''}`}
            onClick={() => setIsAIMode(true)}
          >
            🤖 AI会話モード
          </button>
          <button 
            className={`mode-btn ${!isAIMode ? 'active' : ''}`}
            onClick={() => setIsAIMode(false)}
          >
            ✏️ 手動入力モード
          </button>
        </div>
      </div>

      <main className="main-content">
        <div className="avatar-section">
          <h2>アバター表示エリア</h2>
          <AvatarPlayer 
            isConnected={isConnected}
            setIsConnected={setIsConnected}
            message={message}
            setMessage={setMessage}
            onSpeakWithAvatarReady={handleSpeakWithAvatarReady}
          />
          
          <div className="avatar-status">
            <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
              {isConnected ? '🟢 接続済み' : '🔴 未接続'}
            </span>
          </div>
        </div>

        <div className="interaction-section">
          {isAIMode ? (
            <div className="ai-chat-section">
              <h3>AI アシスタント (GPT-4.1)</h3>
              <ChatInterface 
                onNewMessage={handleAIResponse}
                className="ai-chat-interface"
                speakWithAvatarFunction={speakWithAvatarFunction}
              />
              <p className="ai-description">
                AIとの会話内容が自動的にアバターで音声合成されます
              </p>
            </div>
          ) : (
            <div className="manual-input-section">
              <h3>手動テキスト入力</h3>
              <div className="manual-controls">
                <input
                  type="text"
                  className="text-input"
                  placeholder="アバターに話させたいテキストを入力してください"
                  value={message}
                  onChange={handleManualInput}
                />
                <p className="manual-description">
                  入力したテキストがアバターで音声合成されます
                </p>
              </div>
            </div>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <div className="footer-content">
          <div className="footer-section">
            <h4>技術スタック</h4>
            <ul>
              <li>GPT-4.1 (Azure OpenAI Service)</li>
              <li>Azure Speech Service</li>
              <li>React + TypeScript</li>
              <li>FastAPI + Python</li>
            </ul>
          </div>
          <div className="footer-section">
            <h4>フェーズ1機能</h4>
            <ul>
              <li>リアルタイムAI応答生成</li>
              <li>音声アバター合成</li>
              <li>会話履歴管理</li>
              <li>ストリーミングレスポンス</li>
            </ul>
          </div>
          <div className="footer-section">
            <h4>今後の実装予定</h4>
            <ul>
              <li>RAG検索機能 (フェーズ2)</li>
              <li>音声入力対応 (フェーズ3)</li>
              <li>完全対話ループ (フェーズ4)</li>
            </ul>
          </div>
        </div>
        <p className="copyright">
          PythonとReactを活用したAI強化リアルタイムアバターシステム - Phase 1
        </p>
      </footer>
    </div>
  );
};

export default App;