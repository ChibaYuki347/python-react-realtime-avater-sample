# PythonとReactを活用したリアルタイムカスタムアバターアプリサンプル

本レポジトリではPythonとReactを使用して、リアルタイムでアバターを操作できるアプリケーションのサンプルコードを提供します。
Azure AI Speech サービスのカスタムボイスとカスタムアバターに対応した、プロダクション対応のアプリケーションです。

## ✨ 主な機能

- 🎭 **リアルタイムアバター表示**: Azure Speech サービスを使用したリアルタイムアバター表示
- 🎤 **カスタムボイス対応**: Azure Speech サービスのカスタムボイス（Professional Voice）に完全対応
- 👤 **カスタムアバター対応**: カスタムアバターキャラクターの利用が可能  
- 🔗 **カスタムアバター + カスタムボイス**: カスタムアバターとカスタムボイスの組み合わせをサポート
- ⚙️ **動的設定変更**: UIから音声・アバター設定をリアルタイムで変更
- 🌐 **環境変数対応**: プロダクション環境での柔軟な設定管理
- 🔒 **型安全**: TypeScriptによる完全な型安全性
- 📱 **レスポンシブUI**: モダンで使いやすいユーザーインターフェース
- 🎯 **Azure公式準拠**: Azure Speech Service公式ドキュメントに基づいた正しい実装

## 📁 プロジェクト構成

```
python-react-realtime-avater-sample/
├── backend/                    # FastAPI バックエンド
│   ├── main.py                # メインAPIサーバー
│   ├── requirements.txt       # Python依存関係
│   └── .env.example          # 環境変数テンプレート
├── frontend/                  # React + TypeScript フロントエンド
│   ├── public/               # 静的ファイル
│   ├── src/                  # TypeScriptソースコード
│   │   ├── components/       # Reactコンポーネント
│   │   ├── utils/           # ユーティリティ関数
│   │   ├── types/           # TypeScript型定義
│   │   ├── App.tsx          # メインアプリケーション
│   │   └── index.tsx        # エントリーポイント
│   └── package.json         # Node.js依存関係
├── docs/                     # ドキュメント
└── README.md                # このファイル
```

## 🚀 セットアップ手順

### 前提条件

- Python 3.8以上
- Node.js 16以上
- Azure サブスクリプション
- Azure AI Speech サービスのリソース

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd python-react-realtime-avater-sample
```

### 2. バックエンドのセットアップ

```bash
# バックエンドディレクトリに移動
cd backend

# 仮想環境を作成（推奨）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .envファイルを編集して、Azure Speech サービスの情報を入力
```

### 3. フロントエンドのセットアップ

```bash
# フロントエンドディレクトリに移動
cd ../frontend

# 依存関係をインストール
npm install
```

### 4. Azure Speech サービスの設定

1. [Azure Portal](https://portal.azure.com)でAI Speechサービスのリソースを作成
2. リソースの「キーとエンドポイント」からキーとリージョンを取得
3. `backend/.env`ファイルを編集：

```env
# Azure Speech Service Configuration
SPEECH_KEY=your-speech-service-key
SPEECH_REGION=your-speech-service-region

# Server Configuration
PORT=8000

# 音声設定
# 標準音声の例: ja-JP-NanamiNeural, en-US-AriaNeural
# カスタム音声の例: YourCustomVoiceName (リアルタイム合成ではボイス名をそのまま指定)
DEFAULT_VOICE_NAME=Inoue-MultiLingual-Fast
DEFAULT_VOICE_LANGUAGE=ja-JP

# アバター設定
# 標準アバター: lisa, anna
# カスタムアバター: YourCustomAvatarName
DEFAULT_AVATAR_CHARACTER=Inoue
DEFAULT_AVATAR_STYLE=ja-normal

# アバタービデオフォーマット
DEFAULT_VIDEO_FORMAT=mp4

# カスタムアバター設定
CUSTOM_AVATAR_ENABLED=true

# 利用可能なカスタムボイス（カンマ区切り）
# リアルタイム合成では、ボイス名を直接speechSynthesisVoiceNameに設定
AVAILABLE_CUSTOM_VOICES=Inoue-MultiLingual-Fast,ja-JP-NanamiNeural,en-US-AriaNeural

# カスタムボイスのデプロイメントID（JSON形式）
# リアルタイム合成でendpointIdとして使用
CUSTOM_VOICE_DEPLOYMENT_IDS={"Inoue-MultiLingual-Fast": "your-deployment-id"}
```
DEFAULT_AVATAR_STYLE=casual-sitting
DEFAULT_VIDEO_FORMAT=mp4

# カスタムアバター設定 (高度な設定)
CUSTOM_AVATAR_ENABLED=false
CUSTOM_AVATAR_CHARACTER=
CUSTOM_AVATAR_STYLE=

# カスタムボイス設定 (高度な設定)
CUSTOM_VOICE_ENABLED=false
CUSTOM_VOICE_NAME=
CUSTOM_VOICE_DEPLOYMENT_ID=
```

## 💻 実行方法

### バックエンドサーバーの起動

```bash
cd backend
python main.py
```

サーバーは http://localhost:8000 で起動します。

### フロントエンドアプリケーションの起動

```bash
cd frontend
npm start
```

アプリケーションは http://localhost:3000 で起動します。

## 🎭 使用方法

### 基本的な使い方

1. **アプリケーションにアクセス**
   - http://localhost:3000 をブラウザで開く

2. **設定の確認**
   - 上部の設定パネルで現在の設定を確認
   - 利用可能なボイス一覧から選択可能
   - 音声名: `ja-JP-NanamiNeural`, `en-US-AriaNeural`, `Inoue-MultiLingual-Fast` など
   - アバターキャラクター: `lisa`, `anna`, `Inoue` など
   - アバタースタイル: `casual-sitting`, `ja-normal` など

3. **アバターに接続**
   - 「アバターに接続」ボタンをクリック
   - 接続が完了するまで数秒待機
   - デバッグ情報でリアルタイムな接続状況を確認可能

4. **音声合成の実行**
   - テキスト入力欄にアバターに話させたい内容を入力
   - 「アバターに話させる」ボタンでアバターが話します

### カスタムボイス・アバターの使用方法

#### 🎯 重要なポイント
このアプリケーションは **リアルタイム合成** に対応しており、Azure Speech Service公式ドキュメントに基づいて実装されています。

#### カスタムボイスの設定

**Professional Voice の場合:**
1. Azure Speech サービスでProfessional Voiceを作成・デプロイ
2. 環境変数でカスタムボイスを設定：
```env
AVAILABLE_CUSTOM_VOICES=YourCustomVoice-MultiLingual-Fast,ja-JP-NanamiNeural
CUSTOM_VOICE_DEPLOYMENT_IDS={"YourCustomVoice-MultiLingual-Fast": "your-deployment-id"}
```
3. UIでカスタムボイスを選択して使用

**Voice Sync for Avatar の場合:**
- カスタムアバター作成時に同時にトレーニングされる音声
- 対象アバター専用で、独立使用は不可
- アプリケーションが自動的に適切な設定を適用

#### カスタムアバターの設定
1. Azure Speech サービスでカスタムアバターを作成・デプロイ
2. 環境変数でカスタムアバターを設定：
```env
CUSTOM_AVATAR_ENABLED=true
DEFAULT_AVATAR_CHARACTER=YourCustomAvatar
DEFAULT_AVATAR_STYLE=your-style
```
3. カスタムボイスとの組み合わせが可能

#### 🔧 技術的な実装詳細

**リアルタイム合成での重要な設定:**
- **SpeechConfig.endpointId**: カスタムボイス使用時にデプロイメントIDを設定
- **AvatarConfig.useBuiltInVoice**: カスタムアバター使用時の音声制御
  - `true`: Voice Sync for Avatar使用
  - `false`: 外部カスタムボイス使用
- **SpeechConfig.speechSynthesisVoiceName**: ボイス名を直接指定

## 🏗️ 技術スタック

### バックエンド
- **FastAPI**: 高性能なPython Webフレームワーク
- **Azure AI Speech SDK**: 音声認証トークンの取得とICEサーバー情報取得
- **CORS対応**: フロントエンドとの安全な通信
- **環境変数管理**: プロダクション対応の設定管理
- **JSON設定管理**: カスタムボイスデプロイメントIDの動的管理

### フロントエンド
- **React 18 + TypeScript**: 型安全なユーザーインターフェース
- **Microsoft Cognitive Services Speech SDK**: リアルタイム音声合成とアバター表示
- **WebRTC**: P2Pリアルタイム通信
- **Axios**: 型安全なHTTP通信
- **完全な型定義**: エラーを防ぐTypeScript型システム
- **レスポンシブデザイン**: モバイル対応UI
- **動的設定管理**: リアルタイムでのボイス・アバター切り替え

## 📝 機能一覧

### ✅ 実装済み機能
- **認証・接続**
  - Azure Speech サービス認証
  - WebRTCによるP2P接続  
  - ICEサーバー最適化
  - 自動再接続機能

- **アバター機能**
  - リアルタイムアバター表示
  - 標準アバター（lisa, anna等）
  - カスタムアバター対応
  - アバタースタイル変更
  - **カスタムアバター + カスタムボイス組み合わせ**

- **音声機能**  
  - テキスト音声合成
  - 標準音声（日本語、英語等）
  - **Professional Voice 完全対応**
  - **Voice Sync for Avatar 対応**
  - SSML対応
  - **リアルタイム合成最適化**

- **設定管理**
  - UIからの動的設定変更
  - 環境変数による事前設定
  - **カスタムボイスデプロイメントID管理**
  - **動的ボイス・アバター切り替え**
  - リアルタイム設定反映

- **ユーザビリティ**
  - レスポンシブUI
  - **詳細なデバッグ情報表示**
  - エラーハンドリング
  - **接続状態リアルタイム監視**
  - **Azure公式準拠実装**
  - リアルタイムデバッグ情報
  - エラーハンドリング
  - 接続状態表示

### 🚧 今後の拡張可能性
- バッチ音声合成機能
- 多言語同時対応
- アバター感情表現
- ユーザー認証機能

## ⚠️ 注意事項・制限事項

### 技術的制限
- **ブラウザ対応**: Chrome、Microsoft Edge、Firefox の最新版を推奨
- **WebRTC制限**: 企業ファイアウォール環境では接続できない場合があります
- **アイドルタイムアウト**: アバター接続は5分間のアイドル制限があります
- **同時接続数**: 開発環境では同時接続数に制限があります

### カスタムボイス・アバターの制限
- **Professional Voice**: リアルタイム合成で完全対応（endpointId設定済み）
- **Voice Sync for Avatar**: カスタムアバター専用音声として自動適用
- **リージョン制限**: カスタムリソースは特定のリージョンでのみ利用可能
- **デプロイメントID**: 環境変数での正確な設定が必要

### 本番環境での考慮事項
- **ICEサーバー**: 本番環境では専用TURNサーバーを推奨
- **認証強化**: より厳密な認証機構の実装を推奨
- **スケーリング**: Load Balancer と複数インスタンス対応
- **コスト最適化**: Azure Speech サービス利用料金の監視が重要

## 🔗 API リファレンス

### バックエンド API エンドポイント

#### `GET /api/config`
アプリケーション設定を取得

**レスポンス例:**
```json
{
  "voice": {
    "defaultName": "Inoue-MultiLingual-Fast",
    "defaultLanguage": "ja-JP"
  },
  "avatar": {
    "defaultCharacter": "Inoue", 
    "defaultStyle": "ja-normal",
    "defaultVideoFormat": "mp4"
  },
  "availableCustomVoices": [
    "Inoue-MultiLingual-Fast",
    "ja-JP-NanamiNeural", 
    "en-US-AriaNeural"
  ],
  "customVoiceDeploymentIds": {
    "Inoue-MultiLingual-Fast": "0d890981-5f4d-4821-94b2-50ba46fb7400"
  },
  "customAvatar": {
    "enabled": true
  },
  "region": "southeastasia"
}
```

#### `GET /api/get-speech-token`
Azure Speech サービス認証トークンを取得

**レスポンス例:**
```json
{
  "authToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "region": "southeastasia"
}
```

#### `GET /api/get-ice-server-info`  
WebRTC用ICEサーバー情報を取得

**レスポンス例:**
```json
[
  {
    "urls": ["stun:stun.l.google.com:19302"]
  },
  {
    "urls": ["turn:turnserver.com:3478"],
    "username": "user",
    "credential": "pass"
  }
]
```

## 🔧 カスタマイズガイド

### 標準設定の変更

環境変数を使用してデフォルト設定を変更：

```env
# 日本語アバター（女性）
DEFAULT_VOICE_NAME=ja-JP-NanamiNeural
DEFAULT_AVATAR_CHARACTER=lisa

# 英語アバター（男性）
DEFAULT_VOICE_NAME=en-US-BrianNeural  
DEFAULT_AVATAR_CHARACTER=tim
DEFAULT_AVATAR_STYLE=formal-standing
```

### 利用可能な標準アバター

| キャラクター | 説明 | 対応スタイル |
|------------|------|------------|
| `lisa` | アジア系女性 | `casual-sitting`, `formal-standing` |
| `anna` | 西欧系女性 | `casual-sitting`, `business-standing` |
| `tim` | 西欧系男性 | `formal-standing`, `casual-sitting` |

### 利用可能な標準音声（一例）

| 言語 | 音声名 | 性別 |
|------|--------|------|
| 日本語 | `ja-JP-NanamiNeural` | 女性 |
| 日本語 | `ja-JP-KeitaNeural` | 男性 |
| 英語(US) | `en-US-AriaNeural` | 女性 |
| 英語(US) | `en-US-BrianNeural` | 男性 |

### コードでの詳細カスタマイズ

高度なカスタマイズが必要な場合：

#### アバター設定の変更
```typescript
// frontend/src/components/AvatarPlayer.tsx
const avatarConfig = new speechSdk.AvatarConfig(
    "your-custom-character", 
    "your-custom-style",
    "mp4" // または "webm"
);
```

#### 音声設定の変更
```typescript
// Speech Configの設定
speechConfig.speechSynthesisLanguage = "ja-JP";
speechConfig.speechSynthesisVoiceName = "ja-JP-NanamiNeural";
```

## 🚨 トラブルシューティング

### よくある問題と解決方法

#### 1. アバターが表示されない
- **原因**: ブラウザがWebRTCに対応していない
- **解決方法**: Chrome、Edge、Firefox の最新版を使用

#### 2. 音声が出ない  
- **原因**: ブラウザの自動再生ポリシー
- **解決方法**: ブラウザの設定で自動再生を許可

#### 3. 接続が頻繁に切断される
- **原因**: ネットワーク不安定またはICEサーバー問題
- **解決方法**: 安定したネットワーク環境を使用

#### 4. カスタムアバターが動作しない
- **原因**: `customized: true` が設定されていない
- **解決方法**: UIで「カスタムアバター使用」をチェック

#### 5. バックエンドAPI エラー
- **原因**: 環境変数が正しく設定されていない
- **解決方法**: `.env`ファイルの設定を確認し、バックエンドを再起動

### デバッグ情報の確認

アプリケーション下部のデバッグ情報パネルで詳細なログを確認できます：
- 接続状態
- エラーメッセージ  
- 設定値
- 通信ログ

## 🏗️ 実装詳細

### リアルタイム合成でのカスタムボイス実装

本アプリケーションは、Azure Speech Service公式ドキュメントに基づいて、リアルタイム合成でのカスタムボイス対応を正しく実装しています。

#### 重要な実装ポイント

**1. SpeechConfig設定**
```typescript
const speechConfig = speechSdk.SpeechConfig.fromAuthorizationToken(authToken, region);
speechConfig.speechSynthesisVoiceName = voiceName;

// カスタムボイス使用時の重要な設定
if (customVoiceEnabled && deploymentId) {
    (speechConfig as any).endpointId = deploymentId;
}
```

**2. AvatarConfig設定**
```typescript
const avatarConfig = new speechSdk.AvatarConfig(character, style, videoFormat);

if (customAvatarEnabled) {
    (avatarConfig as any).customized = true;
    
    // カスタムアバター + カスタムボイスの制御
    if (customVoiceEnabled) {
        (avatarConfig as any).useBuiltInVoice = false; // 外部カスタムボイス使用
    } else {
        (avatarConfig as any).useBuiltInVoice = true;  // Voice Sync for Avatar使用
    }
}
```

#### Azure公式サンプルとの対応関係

| Azure公式サンプル | 本実装 | 説明 |
|---|---|---|
| `endpointId` | `speechConfig.endpointId` | カスタムボイスのデプロイメントID |
| `useBuiltInVoice` | `avatarConfig.useBuiltInVoice` | アバター内蔵音声の使用制御 |
| `customized` | `avatarConfig.customized` | カスタムアバターフラグ |

### 設定管理の仕組み

**バックエンド（環境変数）→ API → フロントエンド**の流れで設定を管理：

1. **環境変数**: 管理者が設定
2. **FastAPI**: 設定をAPIで提供
3. **React**: 動的に設定を取得・反映
4. **Azure SDK**: 正しいパラメータでリアルタイム合成

## 📚 参考資料

- [Azure AI Speech サービス ドキュメント](https://learn.microsoft.com/ja-jp/azure/ai-services/speech-service/)
- [Custom text to speech avatar overview](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech-avatar/what-is-custom-text-to-speech-avatar)
- [Real-time synthesis for text to speech avatar](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech-avatar/real-time-synthesis-avatar)
- [リアルタイム音声合成の仕組み](./docs/realtime-synthesis-mechanism.md)
- [Microsoft Speech SDK for JavaScript](https://github.com/Microsoft/cognitive-services-speech-sdk-js)
- [Azure Speech SDK サンプル](https://github.com/Azure-Samples/cognitive-services-speech-sdk/blob/master/samples/js/browser/avatar/js/basic.js)

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で提供されています。