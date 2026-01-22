#!/usr/bin/env python3
"""
Azure RAGサービスのヘルスチェック用テストスクリプト
"""
import requests
import sys

def test_health_endpoint():
    """ヘルスチェックエンドポイントをテスト"""
    try:
        print("Testing Azure RAG Health endpoint...")
        response = requests.get('http://localhost:8000/api/azure-rag/health', timeout=5)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Health check passed!")
            return True
        else:
            print("❌ Health check failed!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure server is running on port 8000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_health_endpoint()
    sys.exit(0 if success else 1)