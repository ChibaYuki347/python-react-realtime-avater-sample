"""
Azure Speech-to-Text API ルート
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import azure.cognitiveservices.speech as speechsdk
from app.services.azure_rag_service import AzureRAGService
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/speech", tags=["speech"])

# グローバル RAG サービスインスタンス
rag_service = None


async def get_rag_service():
    global rag_service
    if rag_service is None:
        rag_service = AzureRAGService()
        await rag_service.initialize()
    return rag_service


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), rag_service = Depends(get_rag_service)):
    """
    音声ファイルを受け取り、テキストに変換
    
    Args:
        file: 音声ファイル（WAV, PCM 等）
    
    Returns:
        JSON: {"text": "認識したテキスト"}
    """
    try:
        # 環境変数から認証情報を取得
        speech_key = os.getenv("SPEECH_KEY")
        speech_region = os.getenv("SPEECH_REGION")
        
        if not speech_key or not speech_region:
            logger.error("Speech API credentials not configured")
            raise HTTPException(
                status_code=500,
                detail="Speech API credentials are not configured"
            )
        
        # 音声ファイルを一時的に保存
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        
        # Azure Speech Recognizer を設定
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=speech_region
        )
        
        # 言語を日本語に設定
        speech_config.speech_recognition_language = "ja-JP"
        
        # ファイルから音声を読み込み
        audio_config = speechsdk.audio.AudioConfig(filename=temp_file_path)
        
        # Speech Recognizer を作成
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        logger.info(f"Starting speech recognition for file: {file.filename}")
        
        # 音声認識を実行
        result = recognizer.recognize_once()
        
        # 一時ファイルを削除
        os.remove(temp_file_path)
        
        # 結果を処理
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            recognized_text = result.text
            logger.info(f"Speech recognized: {recognized_text}")
            
            return JSONResponse({
                "success": True,
                "text": recognized_text,
                "confidence": 1.0
            })
        
        elif result.reason == speechsdk.ResultReason.NoMatch:
            logger.warning("No speech recognized")
            return JSONResponse({
                "success": False,
                "text": "",
                "error": "No speech could be recognized"
            })
        
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            logger.error(f"Speech recognition canceled: {cancellation.reason}")
            logger.error(f"Error details: {cancellation.error_details}")
            
            return JSONResponse({
                "success": False,
                "text": "",
                "error": f"Speech recognition canceled: {cancellation.error_details}"
            })
    
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Speech-to-Text error: {str(e)}"
        )


@router.get("/health")
async def speech_health():
    """
    Speech-to-Text サービスのヘルスチェック
    """
    try:
        speech_key = os.getenv("SPEECH_KEY")
        speech_region = os.getenv("SPEECH_REGION")
        
        if not speech_key or not speech_region:
            return JSONResponse({
                "status": "unhealthy",
                "message": "Speech API credentials not configured"
            }, status_code=503)
        
        return JSONResponse({
            "status": "healthy",
            "service": "Azure Speech-to-Text",
            "region": speech_region
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return JSONResponse({
            "status": "unhealthy",
            "message": str(e)
        }, status_code=503)
