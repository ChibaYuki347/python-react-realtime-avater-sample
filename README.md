# PythonとReactを活用したリアルタイムカスタムアバターアプリサンプル

本レポジトリではPythonとReactを使用して、リアルタイムでアバターを操作できるアプリケーションのサンプルコードを提供します。
Azure AI Speech サービスのカスタムボイスとカスタムアバターに対応した、プロダクション対応のアプリケーションです。

## ✨ 主な機能

- 🎭 **リアルタイムアバター表示**: Azure Speech サービスを使用したリアルタイムアバター表示
- 🎤 **カスタムボイス対応**: カスタム音声モデルの利用が可能
- 👤 **カスタムアバター対応**: カスタムアバターキャラクターの利用が可能  
- ⚙️ **動的設定変更**: UIから音声・アバター設定をリアルタイムで変更
- 🌐 **環境変数対応**: プロダクション環境での柔軟な設定管理
- 🔒 **型安全**: TypeScriptによる完全な型安全性
- 📱 **レスポンシブUI**: モダンで使いやすいユーザーインターフェース

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

# カスタム音声設定 (オプション)
DEFAULT_VOICE_NAME=ja-JP-NanamiNeural
DEFAULT_VOICE_LANGUAGE=ja-JP

# カスタムアバター設定 (オプション)
DEFAULT_AVATAR_CHARACTER=lisa
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

2. **設定の調整**（オプション）
   - 上部の設定パネルで音声やアバターをカスタマイズ
   - 音声名: `ja-JP-NanamiNeural`, `en-US-AriaNeural` など
   - アバターキャラクター: `lisa`, `anna` など
   - アバタースタイル: `casual-sitting`, `formal-standing` など

3. **アバターに接続**
   - 「アバターに接続」ボタンをクリック
   - 接続が完了するまで数秒待機

4. **音声合成の実行**
   - テキスト入力欄にアバターに話させたい内容を入力
   - 「アバターに話させる」ボタンでアバターが話します

### カスタムボイス・アバターの使用方法

#### カスタムボイスの設定
1. Azure Speech サービスでカスタムボイスを作成・デプロイ
2. 設定パネルで「カスタムボイス使用」をチェック
3. Deployment IDを入力
4. 音声名にカスタムボイス名を入力

#### カスタムアバターの設定
1. Azure Speech サービスでカスタムアバターを作成・デプロイ
2. 設定パネルで「カスタムアバター使用」をチェック
3. アバターキャラクターにカスタムアバター名を入力

#### 環境変数での事前設定
プロダクション環境では `.env` ファイルで事前設定可能：

```env
# カスタムボイスの有効化
CUSTOM_VOICE_ENABLED=true
CUSTOM_VOICE_NAME=YourCustomVoice-Neural
CUSTOM_VOICE_DEPLOYMENT_ID=your-deployment-id

# カスタムアバターの有効化
CUSTOM_AVATAR_ENABLED=true
CUSTOM_AVATAR_CHARACTER=YourCustomAvatar
CUSTOM_AVATAR_STYLE=custom-pose
```

## 🏗️ 技術スタック

### バックエンド
- **FastAPI**: 高性能なPython Webフレームワーク
- **Azure AI Speech SDK**: 音声認証トークンの取得とICEサーバー情報取得
- **CORS対応**: フロントエンドとの安全な通信
- **環境変数管理**: プロダクション対応の設定管理

### フロントエンド
- **React 18 + TypeScript**: 型安全なユーザーインターフェース
- **Microsoft Cognitive Services Speech SDK**: リアルタイム音声合成とアバター表示
- **WebRTC**: P2Pリアルタイム通信
- **Axios**: 型安全なHTTP通信
- **完全な型定義**: エラーを防ぐTypeScript型システム
- **レスポンシブデザイン**: モバイル対応UI

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

- **音声機能**  
  - テキスト音声合成
  - 標準音声（日本語、英語等）
  - カスタムボイス対応
  - SSML対応

- **設定管理**
  - UIからの動的設定変更
  - 環境変数による事前設定
  - 設定の永続化
  - リアルタイム設定反映

- **ユーザビリティ**
  - レスポンシブUI
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
- **カスタムボイス**: リアルタイムSDKでは限定的なサポート（Batch APIを推奨）
- **カスタムアバター**: Azure Speech サービスでの事前作成・デプロイが必要
- **リージョン制限**: カスタムリソースは特定のリージョンでのみ利用可能

### 本番環境での考慮事項
- **ICEサーバー**: デモ用STUNサーバーを使用、本番環境ではTURNサーバーが必要
- **認証**: 現在は開発用の認証方式、本番環境ではより厳密な認証が必要
- **スケーリング**: 大量のユーザーには Load Balancer と複数インスタンスが必要
- **コスト**: Azure Speech サービスの利用料金に注意

## 🔗 API リファレンス

### バックエンド API エンドポイント

#### `GET /api/config`
アプリケーション設定を取得

**レスポンス例:**
```json
{
  "voice": {
    "defaultName": "ja-JP-NanamiNeural",
    "defaultLanguage": "ja-JP"
  },
  "avatar": {
    "defaultCharacter": "lisa",
    "defaultStyle": "casual-sitting",
    "defaultVideoFormat": "mp4"
  },
  "customVoice": {
    "enabled": false,
    "name": "",
    "deploymentId": ""
  },
  "customAvatar": {
    "enabled": false,
    "character": "",
    "style": ""
  },
  "region": "eastus"
}
```

#### `GET /api/get-speech-token`
Azure Speech サービス認証トークンを取得

#### `GET /api/get-ice-server-info`  
WebRTC用ICEサーバー情報を取得

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

## 📚 参考資料

- [Azure AI Speech サービス ドキュメント](https://learn.microsoft.com/ja-jp/azure/ai-services/speech-service/)
- [リアルタイム音声合成の仕組み](./docs/realtime-synthesis-mechanism.md)
- [Microsoft Speech SDK for JavaScript](https://github.com/Microsoft/cognitive-services-speech-sdk-js)

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で提供されています。