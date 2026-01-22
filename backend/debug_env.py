#!/usr/bin/env python3
"""
環境変数デバッグ用スクリプト
"""
import os
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

print("Environment Variables Debug:")
print("=" * 50)

# RAG関連の環境変数をチェック
rag_vars = [
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_STORAGE_CONTAINER_NAME", 
    "AZURE_SEARCH_SERVICE_ENDPOINT",
    "AZURE_SEARCH_API_KEY",
    "AZURE_SEARCH_INDEX_NAME",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_OPENAI_API_VERSION"
]

for var in rag_vars:
    value = os.getenv(var)
    if value:
        # セキュリティのため、キーの場合は最初の10文字のみ表示
        if "KEY" in var or "CONNECTION_STRING" in var:
            display_value = value[:10] + "..." if len(value) > 10 else value
        else:
            display_value = value
        print(f"✅ {var}: {display_value}")
    else:
        print(f"❌ {var}: Not set")

print("=" * 50)