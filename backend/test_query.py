#!/usr/bin/env python3
"""
Azure RAGサービスのクエリテスト用スクリプト
"""
import requests
import json
import sys

def test_query_endpoint():
    """クエリエンドポイントをテスト"""
    try:
        print("Testing Azure RAG Query endpoint...")
        
        test_query = {
            "query": "このプロジェクトについて教えてください",
            "user_id": "test_user",
            "max_results": 3
        }
        
        response = requests.post(
            'http://localhost:8000/api/azure-rag/query', 
            json=test_query,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Answer: {result.get('answer', 'No answer')}")
            print(f"Query: {result.get('query', 'No query')}")
            print(f"Documents: {len(result.get('relevant_documents', []))}")
            print("✅ Query test passed!")
            return True
        else:
            print(f"Response: {response.text}")
            print("❌ Query test failed!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure server is running on port 8000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_query_endpoint()
    sys.exit(0 if success else 1)