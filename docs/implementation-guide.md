# 実装ガイド: AI強化アバターシステム開発

## 開発準備

### 1. 開発環境のセットアップ

#### 必要な Azure リソース

```bash
# Azure CLI でリソース作成
az group create --name avatar-ai-rg --location japaneast

# Azure Speech Service
az cognitiveservices account create \
  --name avatar-speech-service \
  --resource-group avatar-ai-rg \
  --kind SpeechServices \
  --sku S0 \
  --location japaneast

# Azure OpenAI Service  
az cognitiveservices account create \
  --name avatar-openai-service \
  --resource-group avatar-ai-rg \
  --kind OpenAI \
  --sku S0 \
  --location japaneast

# Azure AI Search
az search service create \
  --name avatar-search-service \
  --resource-group avatar-ai-rg \
  --sku Standard \
  --location japaneast

# Azure Cosmos DB
az cosmosdb create \
  --name avatar-cosmos-db \
  --resource-group avatar-ai-rg \
  --default-consistency-level Session \
  --locations regionName=japaneast failoverPriority=0
```

#### 環境変数の設定

```bash
# backend/.env に追加
# Azure OpenAI/GitHub Models設定
AZURE_OPENAI_ENDPOINT=https://avatar-openai-service.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-02-01

# Azure AI Search設定
AZURE_SEARCH_SERVICE_NAME=avatar-search-service
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=documents-index
AZURE_SEARCH_SEMANTIC_CONFIG_NAME=semantic-config

# Azure Cosmos DB設定
COSMOS_DB_ENDPOINT=https://avatar-cosmos-db.documents.azure.com:443/
COSMOS_DB_KEY=your-cosmos-key
COSMOS_DB_DATABASE_NAME=avatar_conversations

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=your-key
```

### 2. 依存関係の追加

#### Python (Backend)

```bash
cd backend
pip install -r requirements-extended.txt
```

```txt
# requirements-extended.txt に追加
# AI関連
azure-ai-textanalytics==5.3.0
azure-search-documents==11.4.0
azure-cosmos==4.5.1
openai==1.12.0

# WebSocket
websockets==12.0
python-socketio==5.10.0

# 音声処理
soundfile==0.12.1
numpy==1.24.3

# キャッシュ
redis==5.0.1

# 監視
azure-monitor-opentelemetry==1.2.0
opencensus-ext-azure==1.1.13
structlog==23.2.0

# 非同期処理
celery==5.3.4

# セキュリティ
cryptography==41.0.7
python-jose[cryptography]==3.3.0
```

#### Node.js (Frontend)

```bash
cd frontend
npm install --save-dev @types/dom-mediacapture-record
npm install socket.io-client @azure/cosmos microphone-stream
```

```json
// package.json に追加
{
  "dependencies": {
    "socket.io-client": "^4.7.4",
    "@azure/cosmos": "^4.0.0", 
    "microphone-stream": "^6.0.1",
    "wavefile": "^11.0.0",
    "@microsoft/applicationinsights-web": "^3.0.5"
  },
  "devDependencies": {
    "@types/dom-mediacapture-record": "^1.0.16"
  }
}
```

## フェーズ1: 生成AI応答システム実装

### 1. バックエンド: AIサービスの実装

#### AI Service Provider

```python
# backend/services/ai_service.py
from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator
import openai
import os
from azure.identity import DefaultAzureCredential

class AIServiceProvider(ABC):
    @abstractmethod
    async def generate_response(
        self, 
        message: str, 
        context: Optional[str] = None,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        pass

class AzureOpenAIProvider(AIServiceProvider):
    def __init__(self):
        self.client = openai.AsyncAzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION")
        )
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    async def generate_response(
        self, 
        message: str, 
        context: Optional[str] = None,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        system_message = """あなたはフレンドリーなAIアシスタントです。
        ユーザーの質問に対して、親しみやすく丁寧に回答してください。
        回答は簡潔で分かりやすくしてください。"""
        
        messages = [{"role": "system", "content": system_message}]
        
        if context:
            messages.append({"role": "system", "content": f"関連情報: {context}"})
            
        messages.append({"role": "user", "content": message})
        
        if stream:
            return self._generate_stream(messages)
        else:
            return await self._generate_single(messages)
    
    async def _generate_single(self, messages: list) -> str:
        response = await self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    
    async def _generate_stream(self, messages: list) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

# ファクトリーパターン
def get_ai_provider() -> AIServiceProvider:
    provider_type = os.getenv("AI_PROVIDER", "azure_openai")
    
    if provider_type == "azure_openai":
        return AzureOpenAIProvider()
    elif provider_type == "github_models":
        return GitHubModelsProvider()
    else:
        raise ValueError(f"Unknown AI provider: {provider_type}")
```

#### AI API エンドポイント

```python
# backend/routes/ai_routes.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.ai_service import get_ai_provider
from services.conversation_service import ConversationService
import json

router = APIRouter(prefix="/api/ai", tags=["AI"])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = False
    use_rag: bool = False

class ChatResponse(BaseModel):
    response: str
    session_id: str
    confidence: float
    sources: Optional[List[dict]] = None

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        ai_provider = get_ai_provider()
        conversation_service = ConversationService()
        
        # セッション管理
        if not request.session_id:
            session_id = await conversation_service.create_session()
        else:
            session_id = request.session_id
        
        # AI応答生成
        if request.stream:
            return StreamingResponse(
                stream_response(ai_provider, request.message, session_id),
                media_type="text/plain"
            )
        else:
            response = await ai_provider.generate_response(
                message=request.message,
                stream=False
            )
            
            # 会話履歴保存
            await conversation_service.save_message(
                session_id=session_id,
                user_message=request.message,
                ai_response=response
            )
            
            return ChatResponse(
                response=response,
                session_id=session_id,
                confidence=0.9
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def stream_response(ai_provider, message: str, session_id: str):
    """ストリーミング応答の生成"""
    full_response = ""
    async for chunk in ai_provider.generate_response(message, stream=True):
        full_response += chunk
        yield f"data: {json.dumps({'chunk': chunk, 'session_id': session_id})}\n\n"
    
    # 最終応答をデータベースに保存
    conversation_service = ConversationService()
    await conversation_service.save_message(
        session_id=session_id,
        user_message=message,
        ai_response=full_response
    )
    
    yield f"data: {json.dumps({'done': True})}\n\n"
```

### 2. フロントエンド: ChatInterface実装

#### ChatInterface Component

```typescript
// frontend/src/components/ChatInterface.tsx
import React, { useState, useRef, useEffect } from 'react';
import { aiService } from '../services/aiService';
import './ChatInterface.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isTyping?: boolean;
}

interface ChatInterfaceProps {
  onAIResponse: (response: string) => void;
  sessionId?: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  onAIResponse,
  sessionId
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(sessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputText,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const response = await aiService.sendMessage({
        message: inputText,
        sessionId: currentSessionId,
        stream: false
      });

      if (response.sessionId) {
        setCurrentSessionId(response.sessionId);
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // アバターに音声応答を送信
      onAIResponse(response.response);

    } catch (error) {
      console.error('AI応答エラー:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'すみません、エラーが発生しました。もう一度お試しください。',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="message-content">
              {message.content}
            </div>
            <div className="message-timestamp">
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant">
            <div className="message-content typing">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="input-container">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="メッセージを入力..."
          rows={2}
          disabled={isLoading}
        />
        <button 
          onClick={sendMessage}
          disabled={!inputText.trim() || isLoading}
          className="send-button"
        >
          {isLoading ? '送信中...' : '送信'}
        </button>
      </div>
    </div>
  );
};
```

#### AI Service Client

```typescript
// frontend/src/services/aiService.ts
interface ChatRequest {
  message: string;
  sessionId?: string;
  stream?: boolean;
  useRAG?: boolean;
}

interface ChatResponse {
  response: string;
  sessionId: string;
  confidence: number;
  sources?: any[];
}

class AIService {
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  }

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseURL}/api/ai/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  async sendMessageStream(
    request: ChatRequest,
    onChunk: (chunk: string) => void,
    onComplete: () => void
  ): Promise<void> {
    const response = await fetch(`${this.baseURL}/api/ai/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...request, stream: true })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.chunk) {
                onChunk(data.chunk);
              } else if (data.done) {
                onComplete();
                return;
              }
            } catch (e) {
              console.error('JSONパースエラー:', e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async getSessions(): Promise<any[]> {
    const response = await fetch(`${this.baseURL}/api/ai/sessions`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  }

  async deleteSession(sessionId: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/api/ai/sessions/${sessionId}`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  }
}

export const aiService = new AIService();
```

### 3. アプリケーション統合

#### メインApp.tsx の更新

```typescript
// frontend/src/App.tsx に追加
import { ChatInterface } from './components/ChatInterface';

function App() {
  const [currentAIResponse, setCurrentAIResponse] = useState<string>('');
  
  const handleAIResponse = (response: string) => {
    setCurrentAIResponse(response);
    // アバターに音声応答を送信
    // この部分で既存のAvatarPlayerと連携
  };

  return (
    <div className="App">
      <div className="app-container">
        <div className="avatar-section">
          <AvatarPlayer aiResponse={currentAIResponse} />
        </div>
        <div className="chat-section">
          <ChatInterface onAIResponse={handleAIResponse} />
        </div>
      </div>
    </div>
  );
}
```

## テスト・デバッグ

### 1. 単体テスト

#### バックエンドテスト
```python
# backend/tests/test_ai_service.py
import pytest
from services.ai_service import AzureOpenAIProvider

@pytest.mark.asyncio
async def test_ai_response_generation():
    provider = AzureOpenAIProvider()
    response = await provider.generate_response(
        message="こんにちは",
        stream=False
    )
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio  
async def test_ai_streaming_response():
    provider = AzureOpenAIProvider()
    chunks = []
    
    async for chunk in provider.generate_response(
        message="短い詩を作って",
        stream=True
    ):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    full_response = ''.join(chunks)
    assert len(full_response) > 10
```

#### フロントエンドテスト

```typescript
// frontend/src/__tests__/ChatInterface.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInterface } from '../components/ChatInterface';
import { aiService } from '../services/aiService';

// aiServiceをモック
jest.mock('../services/aiService');
const mockAIService = aiService as jest.Mocked<typeof aiService>;

test('メッセージ送信が正常に動作する', async () => {
  const mockResponse = {
    response: 'こんにちは！',
    sessionId: 'test-session',
    confidence: 0.9
  };
  
  mockAIService.sendMessage.mockResolvedValue(mockResponse);
  
  const onAIResponse = jest.fn();
  render(<ChatInterface onAIResponse={onAIResponse} />);
  
  const input = screen.getByPlaceholderText('メッセージを入力...');
  const sendButton = screen.getByText('送信');
  
  fireEvent.change(input, { target: { value: 'テストメッセージ' } });
  fireEvent.click(sendButton);
  
  await waitFor(() => {
    expect(screen.getByText('テストメッセージ')).toBeInTheDocument();
    expect(screen.getByText('こんにちは！')).toBeInTheDocument();
  });
  
  expect(onAIResponse).toHaveBeenCalledWith('こんにちは！');
});
```

### 2. 統合テスト

#### E2E テスト

```typescript
// frontend/src/__tests__/e2e/chat-flow.test.tsx
import { test, expect } from '@playwright/test';

test('完全な対話フローのテスト', async ({ page }) => {
  await page.goto('http://localhost:3000');
  
  // チャット入力
  await page.fill('[placeholder="メッセージを入力..."]', 'こんにちは');
  await page.click('button:has-text("送信")');
  
  // AI応答の待機
  await page.waitForSelector('.message.assistant', { timeout: 10000 });
  
  // アバター動画の確認
  await page.waitForSelector('video', { timeout: 5000 });
  
  const videoElement = await page.$('video');
  const isPlaying = await videoElement?.evaluate((video: HTMLVideoElement) => !video.paused);
  expect(isPlaying).toBeTruthy();
});
```

### 3. 動作確認

#### デバッグ用エンドポイント

```python
# backend/routes/debug_routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/debug", tags=["Debug"])

@router.get("/ai/test")
async def test_ai_connection():
    """AI接続のテスト"""
    try:
        ai_provider = get_ai_provider()
        response = await ai_provider.generate_response(
            message="接続テスト",
            stream=False
        )
        return {"status": "success", "response": response}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.get("/services/health")  
async def health_check():
    """全サービスのヘルスチェック"""
    health_status = {
        "speech_service": await check_speech_service(),
        "ai_service": await check_ai_service(),
        "database": await check_database()
    }
    return health_status
```

## 次のステップ

フェーズ1の実装が完了したら、次は以下を進めます：

1. **フェーズ2**: Azure AI Search + RAG システムの実装
2. **フェーズ3**: 音声入力強化の実装  
3. **フェーズ4**: 全機能統合と最適化

各フェーズの詳細な実装手順は、`docs/next-phase-development-plan.md` を参照してください。

---

*この実装ガイドは開発の進捗に応じて継続的に更新されます。*