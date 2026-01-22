"""
Azure Speech-to-Text API ルート
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import azure.cognitiveservices.speech as speechsdk
import os
import io
import wave
import struct

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/speech", tags=["speech"])


def convert_audio_to_wav(audio_data: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """
    任意のオーディオフォーマットを WAV フォーマットに変換する試行
    """
    try:
        # 入力がすでに WAV フォーマットか確認
        if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
            logger.info("Audio is already in WAV format")
            return audio_data
        
        # WebM/Ogg の場合、PCM データと仮定して WAV ラッパーを作成
        logger.info(f"Converting non-WAV format to WAV (assuming PCM data)")
        
        # WAV ヘッダーを構築
        # サンプルレート 16000 Hz、モノラル、16-bit PCM と仮定
        byte_rate = sample_rate * channels * 2  # 16-bit = 2 bytes
        block_align = channels * 2
        
        wav_header = io.BytesIO()
        wav_header.write(b'RIFF')
        wav_header.write(struct.pack('<I', 36 + len(audio_data)))  # ファイルサイズ - 8
        wav_header.write(b'WAVE')
        
        # fmt サブチャンク
        wav_header.write(b'fmt ')
        wav_header.write(struct.pack('<I', 16))  # サブチャンクサイズ
        wav_header.write(struct.pack('<H', 1))   # オーディオフォーマット (1 = PCM)
        wav_header.write(struct.pack('<H', channels))  # チャンネル数
        wav_header.write(struct.pack('<I', sample_rate))  # サンプリングレート
        wav_header.write(struct.pack('<I', byte_rate))  # バイトレート
        wav_header.write(struct.pack('<H', block_align))  # ブロックアライン
        wav_header.write(struct.pack('<H', 16))  # ビット深度
        
        # data サブチャンク
        wav_header.write(b'data')
        wav_header.write(struct.pack('<I', len(audio_data)))  # データサイズ
        wav_header.write(audio_data)
        
        return wav_header.getvalue()
    
    except Exception as e:
        logger.error(f"Failed to convert audio to WAV: {e}")
        return audio_data


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    音声ファイルを受け取り、テキストに変換
    
    Args:
        file: 音声ファイル（WAV, WebM, Ogg 等）
    
    Returns:
        JSON: {"success": bool, "text": str, "error": str (optional)}
    """
    temp_file_path = None
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
        
        # ファイルコンテンツを読み込み
        file_content = await file.read()
        logger.info(f"Received audio file: {file.filename}")
        logger.info(f"  Size: {len(file_content)} bytes")
        logger.info(f"  Content-Type: {file.content_type}")
        
        # ファイルの先頭バイトを確認
        magic_bytes = file_content[:12]
        logger.info(f"  Magic bytes: {magic_bytes.hex()}")
        
        # 音声ファイル形式を判定
        audio_format = "unknown"
        if file_content[:4] == b'RIFF' and file_content[8:12] == b'WAVE':
            audio_format = "WAV"
        elif file_content[:4] == b'RIFF':
            audio_format = "RIFF (possibly WebM)"
        elif file_content[:4] == b'OggS':
            audio_format = "Ogg"
        elif file_content[:4] == b'ID3 ' or file_content[:3] == b'ID3':
            audio_format = "MP3"
        else:
            # 非標準形式：おそらくブラウザが生成した WebM/Ogg のパーツ
            audio_format = f"Unknown (first bytes: {file_content[:4].hex()})"
        
        logger.info(f"  Detected format: {audio_format}")
        
        # 必要に応じて WAV 形式に変換
        audio_data = convert_audio_to_wav(file_content)
        logger.info(f"  After conversion: {len(audio_data)} bytes")
        
        # 一時ファイルに保存
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_file_path = tmp.name
            tmp.write(audio_data)
        
        logger.info(f"  Saved to: {temp_file_path}")
        
        # ファイルが有効か確認
        file_size = os.path.getsize(temp_file_path)
        logger.info(f"  File size on disk: {file_size} bytes")
        
        # ファイルの最初の20バイトを16進ダンプ
        with open(temp_file_path, 'rb') as f:
            header = f.read(20)
            logger.info(f"  File header: {header.hex()}")
        
        # Azure Speech Recognizer を設定
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=speech_region
        )
        
        # 言語を日本語に設定
        speech_config.speech_recognition_language = "ja-JP"
        
        logger.info("Creating audio config from file...")
        
        # ファイルから音声を読み込み
        try:
            audio_config = speechsdk.audio.AudioConfig(filename=temp_file_path)
            logger.info("Audio config created successfully")
        except Exception as e:
            logger.error(f"Failed to create audio config: {e}", exc_info=True)
            raise
        
        # Speech Recognizer を作成
        logger.info("Creating speech recognizer...")
        try:
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            logger.info("Speech recognizer created successfully")
        except Exception as e:
            logger.error(f"Failed to create recognizer: {e}", exc_info=True)
            raise
        
        logger.info("Starting speech recognition...")
        
        # 音声認識を実行
        result = recognizer.recognize_once()
        
        logger.info(f"Recognition result reason: {result.reason}")
        
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
            logger.error(f"Error code: {cancellation.error_code}")
            logger.error(f"Error details: {cancellation.error_details}")
            
            return JSONResponse({
                "success": False,
                "text": "",
                "error": f"Speech recognition failed: {cancellation.error_details}"
            }, status_code=500)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Speech-to-Text error: {str(e)}"
        )
    
    finally:
        # 一時ファイルを削除
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Deleted temp file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


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
