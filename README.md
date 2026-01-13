# PythonとReactを活用したリアルタイムカスタムアバターアプリサンプル

本レポジトリではPythonとReactを使用して、リアルタイムでアバターを操作できるアプリケーションのサンプルコードを提供します。

## 📁 プロジェクト構成

```
python-react-realtime-avater-sample/
├── backend/                    # FastAPI バックエンド
│   ├── main.py                # メインAPIサーバー
│   ├── requirements.txt       # Python依存関係
│   └── .env.example          # 環境変数テンプレート
├── frontend/                  # React フロントエンド
│   ├── public/               # 静的ファイル
│   ├── src/                  # Reactソースコード
│   │   ├── components/       # Reactコンポーネント
│   │   ├── utils/           # ユーティリティ関数
│   │   ├── App.js           # メインアプリケーション
│   │   └── index.js         # エントリーポイント
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
SPEECH_KEY=your-speech-service-key
SPEECH_REGION=your-speech-service-region
PORT=8000
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

1. アプリケーションにアクセス
2. 「アバターに接続」ボタンをクリック
3. 接続が完了したら、テキスト入力欄にアバターに話させたい内容を入力
4. 「発話開始」ボタンでアバターが話します

## 🏗️ 技術スタック

### バックエンド
- **FastAPI**: 高性能なPython Webフレームワーク
- **Azure AI Speech SDK**: 音声認証トークンの取得
- **CORS対応**: フロントエンドとの通信

### フロントエンド
- **React + TypeScript**: 型安全なユーザーインターフェース
- **Microsoft Cognitive Services Speech SDK**: リアルタイム音声合成
- **WebRTC**: リアルタイム通信
- **Axios**: HTTP通信
- **完全な型定義**: TypeScriptによる型安全な開発環境

## 📝 主な機能

- ✅ Azure Speech サービスとの認証
- ✅ リアルタイムアバター表示
- ✅ テキストからの音声合成
- ✅ WebRTCによるリアルタイム通信
- ✅ レスポンシブなUIデザイン

## ⚠️ 注意事項

- このサンプルではデモ用のICEサーバー（STUN）を使用しています
- 本格的な運用には適切なTURNサーバーの設定が必要です
- Chrome、Microsoft Edgeブラウザでの動作を推奨します
- アバターの接続は5分間のアイドル制限があります

## 🔧 カスタマイズ

### アバターの変更

`frontend/src/components/AvatarPlayer.js` の以下の部分を編集：

```javascript
const avatarConfig = new speechSdk.AvatarConfig(
    "lisa", // アバターキャラクターを変更
    "casual-sitting" // アバタースタイルを変更
);
```

### 音声の変更

```javascript
speechConfig.speechSynthesisLanguage = "ja-JP";
speechConfig.speechSynthesisVoiceName = "ja-JP-NanamiNeural"; // 音声を変更
```

## 📚 参考資料

- [Azure AI Speech サービス ドキュメント](https://learn.microsoft.com/ja-jp/azure/ai-services/speech-service/)
- [リアルタイム音声合成の仕組み](./docs/realtime-synthesis-mechanism.md)
- [Microsoft Speech SDK for JavaScript](https://github.com/Microsoft/cognitive-services-speech-sdk-js)

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で提供されています。