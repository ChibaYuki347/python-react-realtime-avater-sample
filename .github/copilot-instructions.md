# PythonとReactを活用したリアルタイムカスタムアバターアプリサンプル

本レポジトリではPythonとReactを使用して、リアルタイムでアバターを操作できるアプリケーションのサンプルコードを提供します。

## 構成

- **Backend(Python)**: FastAPIを使用してAPIサーバーを構築し、Azure Speech サービスの認証トークン取得とCORS設定を担当します。
- **Frontend(React)**: Reactを使用してユーザーインターフェースを構築し、Azure Speech SDKとWebRTCを使用してリアルタイムアバターを表示します。
- **アバターとボイスモデル**: Azure AI Speech サービスのアバター機能を使用し、カスタムボイスとアバターの組み合わせが可能です。
- **リソース**: Azure Speech サービス上でホストされ、スケーラブルな環境で運用されます。

## 技術詳細

### バックエンド構成
- `backend/main.py`: FastAPIメインアプリケーション
- `backend/requirements.txt`: Python依存関係管理
- `backend/.env.example`: 環境変数テンプレート

### フロントエンド構成
- `frontend/src/App.tsx`: メインReactアプリケーション
- `frontend/src/components/AvatarPlayer.tsx`: アバター表示・制御コンポーネント
- `frontend/src/utils/speechUtils.ts`: Azure Speech SDK関連ユーティリティ

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
- Azure Speech サービスキーはサーバーサイドでのみ使用し、クライアントに露出させません。
- 認証トークンの適切な有効期限管理を行います。
- CORS設定を適切に構成します。


## 参考情報

`docs/realtime-synthesis-mechanism.md`に、Azure Speech SDKを使用したリアルタイムアバター合成の仕組みについて詳しく説明しています。こちらも参照してください。