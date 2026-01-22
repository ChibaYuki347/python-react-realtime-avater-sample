#!/usr/bin/env python3
"""
Azure RAG システムの統合テスト
ドキュメント処理からRAG応答生成までの完全なワークフローをテスト
"""

import requests
import json
import time
from pathlib import Path
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/azure-rag"

class Colors:
    """ターミナル出力用のカラーコード"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_status(message: str, status: str = "INFO"):
    """ステータスメッセージを出力"""
    if status == "SUCCESS":
        print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")
    elif status == "ERROR":
        print(f"{Colors.RED}❌ {message}{Colors.RESET}")
    elif status == "WARNING":
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")
    else:
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")

def print_section(title: str):
    """セクションヘッダーを出力"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}{Colors.RESET}\n")

def test_health_check():
    """ヘルスチェックのテスト"""
    print_section("1. ヘルスチェック")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_status(f"サービスは健全です - Debug Mode: {data.get('debug_mode')}", "SUCCESS")
            print(f"  タイムスタンプ: {data.get('timestamp')}")
            print(f"  初期化状態: {data.get('initialized')}")
            return True
        else:
            print_status(f"ヘルスチェック失敗: {response.status_code}", "ERROR")
            print(f"  応答: {response.text}")
            return False
    except Exception as e:
        print_status(f"エラー: {str(e)}", "ERROR")
        return False

def test_process_folder():
    """フォルダ処理のテスト"""
    print_section("2. ドキュメント処理（data/フォルダ）")
    try:
        data_dir = Path("/Users/chibayuuki/Public/python-react-realtime-avater-sample/data")
        
        # data/フォルダの確認
        if not data_dir.exists():
            print_status(f"data フォルダが見つかりません: {data_dir}", "WARNING")
            return False
        
        files = list(data_dir.glob("*"))
        print_status(f"処理対象ファイル数: {len(files)}", "INFO")
        for f in files:
            print(f"  - {f.name}")
        
        if len(files) == 0:
            print_status("処理対象ファイルがありません", "WARNING")
            return False
        
        # フォルダ処理を実行
        response = requests.post(
            f"{BASE_URL}/process-folder",
            json={"folder_path": str(data_dir)}
        )
        
        if response.status_code == 200:
            result = response.json()
            print_status(f"フォルダ処理成功", "SUCCESS")
            summary = result.get("summary", {})
            print(f"  処理済みファイル数: {summary.get('total_files_processed', 0)}")
            print(f"  失敗ファイル数: {summary.get('total_files_failed', 0)}")
            if summary.get('files_processed'):
                print(f"  処理済みファイル:")
                for f in summary.get('files_processed', []):
                    print(f"    - {f}")
            return True
        else:
            print_status(f"フォルダ処理失敗: {response.status_code}", "ERROR")
            print(f"  応答: {response.text}")
            return False
            
    except Exception as e:
        print_status(f"エラー: {str(e)}", "ERROR")
        return False

def test_create_index():
    """AI Searchインデックス作成のテスト"""
    print_section("3. AI Searchインデックス作成")
    try:
        response = requests.post(f"{BASE_URL}/create-index")
        
        if response.status_code == 200:
            result = response.json()
            print_status(f"インデックス作成成功", "SUCCESS")
            print(f"  インデックス名: {result.get('index_name')}")
            print(f"  メッセージ: {result.get('message')}")
            return True
        else:
            print_status(f"インデックス作成失敗: {response.status_code}", "ERROR")
            print(f"  応答: {response.text}")
            return False
            
    except Exception as e:
        print_status(f"エラー: {str(e)}", "ERROR")
        return False

def test_search(query: str):
    """セマンティック検索のテスト"""
    print_section(f"4. セマンティック検索 - '{query}'")
    try:
        response = requests.post(
            f"{BASE_URL}/search",
            json={
                "query": query,
                "max_results": 3
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            results = result.get("results", [])
            
            if results:
                print_status(f"検索成功 - {len(results)}件の結果", "SUCCESS")
                for i, doc in enumerate(results, 1):
                    print(f"\n  【結果{i}】")
                    print(f"    ファイル: {doc.get('metadata', {}).get('file_name', '不明')}")
                    print(f"    スコア: {doc.get('score', 0):.2f}")
                    content = doc.get('content', '')
                    if len(content) > 100:
                        print(f"    内容: {content[:100]}...")
                    else:
                        print(f"    内容: {content}")
                return True
            else:
                print_status("検索結果が見つかりません", "WARNING")
                return True
        else:
            print_status(f"検索失敗: {response.status_code}", "ERROR")
            print(f"  応答: {response.text}")
            return False
            
    except Exception as e:
        print_status(f"エラー: {str(e)}", "ERROR")
        return False

def test_rag_query(query: str):
    """RAGクエリのテスト（AI応答生成）"""
    print_section(f"5. RAGクエリ（AI応答生成） - '{query}'")
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={
                "query": query,
                "max_results": 3
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print_status("RAG応答生成成功", "SUCCESS")
            print(f"\n📝 AI応答:")
            print(f"  {result.get('answer', '応答なし')}")
            
            docs = result.get('relevant_documents', [])
            if docs:
                print(f"\n📚 参照ドキュメント ({len(docs)}件):")
                for i, doc in enumerate(docs, 1):
                    print(f"  {i}. {doc.get('metadata', {}).get('file_name', '不明')}")
            
            return True
        else:
            print_status(f"RAGクエリ失敗: {response.status_code}", "ERROR")
            print(f"  応答: {response.text}")
            return False
            
    except Exception as e:
        print_status(f"エラー: {str(e)}", "ERROR")
        return False

def main():
    """メインテスト実行"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print("🧪 Azure RAG システム 統合テスト")
    print(f"{'='*60}{Colors.RESET}\n")
    
    test_results = {}
    
    # テスト1: ヘルスチェック
    test_results["ヘルスチェック"] = test_health_check()
    
    if not test_results["ヘルスチェック"]:
        print_status("サービスが利用できません。テストを中止します。", "ERROR")
        return
    
    time.sleep(1)
    
    # テスト2-5: RAG機能（デバッグモードの場合はモック応答）
    test_results["フォルダ処理"] = test_process_folder()
    
    time.sleep(1)
    
    test_results["インデックス作成"] = test_create_index()
    
    time.sleep(1)
    
    # セマンティック検索テスト
    test_results["セマンティック検索"] = test_search("Azureアバターシステムについて")
    
    time.sleep(1)
    
    # RAGクエリテスト
    test_results["RAGクエリ"] = test_rag_query("このプロジェクトの主な機能は何ですか？")
    
    # テスト結果サマリー
    print_section("テスト結果サマリー")
    
    for test_name, result in test_results.items():
        status = "SUCCESS" if result else "ERROR"
        print_status(f"{test_name}: {'成功' if result else '失敗'}", status)
    
    total = len(test_results)
    passed = sum(1 for v in test_results.values() if v)
    
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"総合結果: {passed}/{total} テスト合格")
    print(f"{'='*60}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
