import React, { useState } from 'react';
import AvatarPlayer from './components/AvatarPlayer';
import './index.css';

const App: React.FC = () => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');

  return (
    <div className="app">
      <div className="header">
        <h1>リアルタイムカスタムアバターアプリ</h1>
        <p>Azure Speech SDKを使用したリアルタイム音声合成とアバター表示</p>
      </div>

      <main>
        <div className="avatar-container">
          <h2>アバター表示エリア</h2>
          <AvatarPlayer 
            isConnected={isConnected}
            setIsConnected={setIsConnected}
            message={message}
            setMessage={setMessage}
          />
        </div>

        <div className="controls">
          <h3>コントロール</h3>
          <div>
            <input
              type="text"
              className="text-input"
              placeholder="アバターに話させたいテキストを入力してください"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
          </div>
        </div>
      </main>

      <footer style={{ marginTop: '40px', padding: '20px', borderTop: '1px solid #ddd' }}>
        <p>PythonとReactを活用したリアルタイムカスタムアバターアプリサンプル</p>
      </footer>
    </div>
  );
};

export default App;