# PythonとReactを活用したリアルタイムカスタムアバターアプリサンプル

本レポジトリではPythonとReactを使用して、リアルタイムでアバターを操作できるアプリケーションのサンプルコードを提供します。

## 構成

### 現在の構成
- **Backend(Python)**: FastAPIを使用してAPIサーバーを構築し、Azure Speech サービスの認証トークン取得とCORS設定を担当します。
- **Frontend(React)**: Reactを使用してユーザーインターフェースを構築し、Azure Speech SDKとWebRTCを使用してリアルタイムアバターを表示します。
- **アバターとボイスモデル**: Azure AI Speech サービスのアバター機能を使用し、カスタムボイスとアバターの組み合わせが可能です。
- **リソース**: Azure Speech サービス上でホストされ、スケーラブルな環境で運用されます。

### 次期開発計画（拡張機能）
- **生成AI応答システム**: Azure OpenAI Service/GitHub Modelsを統合し、ユーザーの質問に対する自動応答を生成
- **RAG（検索拡張生成）**: Azure AI Searchを使用してドキュメントのインデックス化と、コンテキストを活用した応答生成
- **音声入力強化**: Azure Speech-to-Textを統合して、ユーザーの音声入力をリアルタイムで認識・処理
- **対話ループの完全自動化**: 音声入力 → 生成AI応答 → アバターによる音声出力の完全なサイクル

## 技術詳細

### 現在のバックエンド構成
- `backend/main.py`: FastAPIメインアプリケーション
- `backend/requirements.txt`: Python依存関係管理
- `backend/.env.example`: 環境変数テンプレート

### 現在のフロントエンド構成
- `frontend/src/App.tsx`: メインReactアプリケーション
- `frontend/src/components/AvatarPlayer.tsx`: アバター表示・制御コンポーネント
- `frontend/src/utils/speechUtils.ts`: Azure Speech SDK関連ユーティリティ

### 次期開発で追加予定のバックエンド構成
- `backend/services/ai_service.py`: Azure OpenAI/GitHub Models統合サービス
- `backend/services/search_service.py`: Azure AI Search統合とRAG実装
- `backend/services/speech_to_text_service.py`: 音声認識サービス
- `backend/models/conversation.py`: 対話履歴管理モデル
- `backend/routes/ai_routes.py`: AI関連エンドポイント

### 次期開発で追加予定のフロントエンド構成
- `frontend/src/components/VoiceInput.tsx`: 音声入力コンポーネント
- `frontend/src/components/ChatInterface.tsx`: 会話インターフェース
- `frontend/src/services/aiService.ts`: AI応答生成サービス
- `frontend/src/utils/audioUtils.ts`: 音声処理ユーティリティ
- `frontend/src/hooks/useVoiceRecognition.ts`: 音声認識カスタムフック

## コーディングルール

## 一般ルール

- コードを変更する場合は必ず確認を得るようにします。
- 変更点はREADMEに記載し、ドキュメントを最新の状態に保ちます。
- 主要な変更点にはコメントを追加し、コードの可読性を向上させます。
- Azure関連のベストプラクティスに従い、セキュリティを重視します。

## Python(FastAPI)コードスタイル
- PEP 8に準拠したコードスタイルを使用します。
- 型ヒントを使用して、コードの可読性を向上させます。
- 適切な例外処理とログ出力を実装します。
- 環境変数を使用した設定管理を行います。

## React(TypeScript)コードスタイル
- 関数コンポーネントとHooksを使用します。
- PropTypesまたはTypeScriptでの型安全性を確保します。
- useEffect、useStateなどのHooksを適切に使用します。
- エラーハンドリングとユーザーフィードバックを実装します。

## セキュリティ要件

### 現在の要件
- Azure Speech サービスキーはサーバーサイドでのみ使用し、クライアントに露出させません。
- 認証トークンの適切な有効期限管理を行います。
- CORS設定を適切に構成します。

### 次期開発で追加される要件
- Azure OpenAI/GitHub Models APIキーの適切な管理と隔離
- Azure AI Search インデックスへのアクセス制御
- ユーザー会話履歴のプライバシー保護とデータ保持ポリシーの実装
- 音声データの一時的な処理と適切な削除
- RAG検索時の機密情報フィルタリング
- レート制限とDoS攻撃対策の実装


## 参考情報

`docs/realtime-synthesis-mechanism.md`に、Azure Speech SDKを使用したリアルタイムアバター合成の仕組みについて詳しく説明しています。こちらも参照してください。