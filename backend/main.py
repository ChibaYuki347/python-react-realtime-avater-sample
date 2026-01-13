from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import httpx
from dotenv import load_dotenv
import logging

# 環境変数を読み込み
load_dotenv()

app = FastAPI(title="リアルタイムアバターAPI", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Reactアプリのポート
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    return {"message": "リアルタイムアバターAPI が正常に動作しています"}

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