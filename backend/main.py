from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
import httpx
from dotenv import load_dotenv
import logging

# 環境変数を最初に読み込む
load_dotenv()

# Import AI routes
from routes.ai_routes import router as ai_router
# Import Azure RAG routes (Blob Storage + AI Search with Managed Identity)
from routes.azure_rag_routes import router as azure_rag_router
# Import Speech-to-Text routes (Azure Speech Service)
from routes.speech_to_text_routes import router as speech_router

app = FastAPI(
    title="AI強化リアルタイムアバターAPI", 
    version="2.0.0",
    description="GPT-4.1統合によるRAG対応AI応答機能付きリアルタイムアバターシステム"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Reactアプリのポート
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.debug("Logging initialized at DEBUG level")

# AI routes registration
app.include_router(ai_router, prefix="/api")
# Azure RAG routes registration (Blob Storage + AI Search with Managed Identity)
app.include_router(azure_rag_router)
# Speech-to-Text routes registration (Azure Speech Service)
app.include_router(speech_router)

# Azure configuration from environment (fallback for local development)
KEY_VAULT_URL = os.getenv("KEY_VAULT_URL", "https://ai-avatar-staging-kv.vault.azure.net/")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "https://ai-avatar-staging-openai.openai.azure.com/")
SPEECH_SERVICE_REGION = os.getenv("SPEECH_SERVICE_REGION", "eastus")

# カスタム音声・アバター設定
DEFAULT_VOICE_NAME = os.getenv("DEFAULT_VOICE_NAME", "ja-JP-NanamiNeural")
DEFAULT_VOICE_LANGUAGE = os.getenv("DEFAULT_VOICE_LANGUAGE", "ja-JP")
DEFAULT_AVATAR_CHARACTER = os.getenv("DEFAULT_AVATAR_CHARACTER", "lisa")
DEFAULT_AVATAR_STYLE = os.getenv("DEFAULT_AVATAR_STYLE", "casual-sitting")
DEFAULT_VIDEO_FORMAT = os.getenv("DEFAULT_VIDEO_FORMAT", "mp4")

# カスタム設定
CUSTOM_AVATAR_ENABLED = os.getenv("CUSTOM_AVATAR_ENABLED", "false").lower() == "true"

# 利用可能なカスタムボイスのリストを取得
AVAILABLE_CUSTOM_VOICES_STR = os.getenv("AVAILABLE_CUSTOM_VOICES", "")
AVAILABLE_CUSTOM_VOICES = [voice.strip() for voice in AVAILABLE_CUSTOM_VOICES_STR.split(",") if voice.strip()] if AVAILABLE_CUSTOM_VOICES_STR else []

# カスタムボイスのデプロイメントIDを取得
try:
    CUSTOM_VOICE_DEPLOYMENT_IDS = json.loads(os.getenv("CUSTOM_VOICE_DEPLOYMENT_IDS", "{}"))
except json.JSONDecodeError:
    CUSTOM_VOICE_DEPLOYMENT_IDS = {}

@app.get("/")
async def root():
    return {
        "message": "AI強化リアルタイムアバターAPI が正常に動作しています",
        "version": "2.0.0",
        "features": [
            "GPT-4.1 AI応答生成",
            "リアルタイムアバター合成",
            "会話履歴管理",
            "Azure統合"
        ],
        "endpoints": {
            "ai_chat": "/ai/chat",
            "ai_stream": "/ai/chat/stream",
            "conversations": "/ai/conversations",
            "health": "/ai/health"
        }
    }

@app.get("/api/config")
async def get_config():
    """アプリケーション設定を取得"""
    try:
        return {
            "voice": {
                "defaultName": DEFAULT_VOICE_NAME,
                "defaultLanguage": DEFAULT_VOICE_LANGUAGE
            },
            "avatar": {
                "defaultCharacter": DEFAULT_AVATAR_CHARACTER,
                "defaultStyle": DEFAULT_AVATAR_STYLE,
                "defaultVideoFormat": DEFAULT_VIDEO_FORMAT
            },
            "availableCustomVoices": AVAILABLE_CUSTOM_VOICES,
            "customVoiceDeploymentIds": CUSTOM_VOICE_DEPLOYMENT_IDS,
            "customAvatar": {
                "enabled": CUSTOM_AVATAR_ENABLED
            },
            "region": os.getenv("SPEECH_REGION")
        }
    except Exception as e:
        logger.error(f"設定取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"設定取得エラー: {str(e)}")

@app.get("/api/get-speech-token")
async def get_speech_token():
    """
    Azure Speech サービスのトークンを取得するエンドポイント
    """
    try:
        speech_key = os.getenv("SPEECH_KEY")
        speech_region = os.getenv("SPEECH_REGION")
        
        if not speech_key or not speech_region:
            raise HTTPException(
                status_code=400,
                detail="SPEECH_KEYまたはSPEECH_REGIONが設定されていません。.envファイルを確認してください。"
            )
        
        if speech_key == "paste-your-speech-key-here" or speech_region == "paste-your-speech-region-here":
            raise HTTPException(
                status_code=400,
                detail="Speech KeyまたはRegionが初期値のままです。.envファイルに正しい値を設定してください。"
            )
        
        # Azure Speech Services Token エンドポイント
        token_url = f"https://{speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        
        headers = {
            "Ocp-Apim-Subscription-Key": speech_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, headers=headers)
            
            if response.status_code == 200:
                token = response.text
                logger.info("Speech トークンが正常に取得されました")
                return JSONResponse(
                    content={"token": token, "region": speech_region},
                    status_code=200
                )
            else:
                logger.error(f"トークン取得エラー: {response.status_code}")
                raise HTTPException(
                    status_code=401,
                    detail="Speech Keyの認証に失敗しました。キーを確認してください。"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"内部サーバーエラーが発生しました: {str(e)}"
        )

@app.get("/api/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "message": "サーバーは正常に動作しています"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)