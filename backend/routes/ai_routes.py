"""
AI-related API routes for GPT-4.1 integration
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio

from services.azure_config import get_configuration
from services.ai_service import get_ai_service, ChatMessage, AIResponse
from models.conversation import conversation_manager, ConversationSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

# Global config cache
_config_cache: Optional[Dict[str, Any]] = None


async def get_cached_config() -> Dict[str, Any]:
    """Get cached configuration or load it"""
    global _config_cache
    if _config_cache is None:
        _config_cache = await get_configuration()
    return _config_cache


# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = 2000
    temperature: Optional[float] = 0.7


class ChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    response: str
    session_id: str
    ai_model: str
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None


class ConversationSummary(BaseModel):
    session_id: str
    message_count: int
    topics: List[str]
    sentiment: str
    context_summary: Optional[str]
    created_at: str
    updated_at: str


@router.get("/health")
async def health_check():
    """AI service health check"""
    try:
        config = await get_cached_config()
        return {
            "status": "healthy",
            "service": "AI Service GPT-4.1",
            "openai_endpoint": config.get("openai_endpoint"),
            "deployment": config.get("openai_deployment_name")
        }
    except Exception as e:
        logger.error(f"AI service health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="AI service unavailable")


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Chat with GPT-4.1 AI assistant
    """
    try:
        # Get or create conversation session
        session = conversation_manager.get_or_create_session(
            session_id=request.session_id,
            user_id=request.user_id
        )
        
        # Add user message to conversation
        session.add_message("user", request.message)
        
        # Get AI service and generate response
        config = await get_cached_config()
        ai_service = await get_ai_service(config)
        
        # Convert conversation history to ChatMessage format
        chat_history = [
            ChatMessage(role=msg.role, content=msg.content, timestamp=msg.timestamp.isoformat())
            for msg in session.get_recent_messages(10)
        ]
        
        # Generate AI response
        ai_response = await ai_service.generate_response(
            user_message=request.message,
            conversation_history=chat_history[:-1],  # Exclude current message
            system_prompt=request.system_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Add assistant response to conversation
        session.add_message("assistant", ai_response.content, {
            "ai_model": ai_response.ai_model,
            "tokens_used": ai_response.tokens_used,
            "response_time": ai_response.response_time
        })
        
        # Schedule background context analysis
        background_tasks.add_task(analyze_conversation_context, session.session_id)
        
        return ChatResponse(
            response=ai_response.content,
            session_id=session.session_id,
            ai_model=ai_response.ai_model,
            tokens_used=ai_response.tokens_used,
            response_time=ai_response.response_time
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate AI response: {str(e)}")


@router.post("/chat/stream")
async def stream_chat_with_ai(request: ChatRequest):
    """
    Stream chat response from GPT-4.1
    """
    try:
        # Get or create conversation session
        session = conversation_manager.get_or_create_session(
            session_id=request.session_id,
            user_id=request.user_id
        )
        
        # Add user message to conversation
        session.add_message("user", request.message)
        
        # Get AI service
        config = await get_cached_config()
        ai_service = await get_ai_service(config)
        
        # Convert conversation history
        chat_history = [
            ChatMessage(role=msg.role, content=msg.content, timestamp=msg.timestamp.isoformat())
            for msg in session.get_recent_messages(10)
        ]
        
        async def generate_stream():
            """Generate streaming response"""
            full_response = ""
            try:
                # Send session info first
                logger.info(f"Starting streaming response for message: {request.message}")
                yield f"data: {json.dumps({'type': 'session', 'session_id': session.session_id})}\n\n"
                
                # Stream AI response
                logger.info("Starting AI service streaming...")
                chunk_count = 0
                async for chunk in ai_service.generate_streaming_response(
                    user_message=request.message,
                    conversation_history=chat_history[:-1],
                    system_prompt=request.system_prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature
                ):
                    chunk_count += 1
                    logger.debug(f"Received chunk {chunk_count}: {chunk[:100]}...")
                    
                    # Extract content from the streaming chunk
                    if chunk.startswith("data: "):
                        try:
                            # Parse the JSON from the chunk
                            json_str = chunk[6:].strip()  # Remove "data: " prefix
                            if json_str:
                                chunk_data = json.loads(json_str)
                                if 'content' in chunk_data:
                                    content = chunk_data['content']
                                    full_response += content
                                    logger.debug(f"Content chunk: {content}")
                                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                                elif chunk_data.get('done'):
                                    logger.info("Received done signal from AI service")
                                    # Don't add done signal to full_response
                                    pass
                        except json.JSONDecodeError:
                            # Fallback: treat as plain text
                            logger.warning(f"Failed to parse JSON, treating as text: {chunk}")
                            full_response += chunk
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                
                logger.info(f"Streaming complete. Full response length: {len(full_response)}")
                logger.debug(f"Full response: {full_response}")
                
                # Add complete response to conversation
                session.add_message("assistant", full_response)
                
                # Send completion signal
                yield f"data: {json.dumps({'type': 'complete', 'full_response': full_response})}\n\n"
                
            except Exception as e:
                logger.error(f"Error in streaming response: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in stream chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stream AI response: {str(e)}")


@router.get("/conversations", response_model=List[ConversationSummary])
async def get_conversations():
    """
    Get list of active conversations
    """
    try:
        sessions = conversation_manager.get_active_sessions()
        
        summaries = [
            ConversationSummary(
                session_id=session.session_id,
                message_count=session.get_conversation_length(),
                topics=session.topics,
                sentiment=session.sentiment,
                context_summary=session.context_summary,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat()
            )
            for session in sessions
        ]
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")


@router.get("/conversations/{session_id}")
async def get_conversation_details(session_id: str):
    """
    Get detailed conversation history
    """
    try:
        session = conversation_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "context_summary": session.context_summary,
            "topics": session.topics,
            "sentiment": session.sentiment,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in session.messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation details")


@router.delete("/conversations/{session_id}")
async def delete_conversation(session_id: str):
    """
    Delete a conversation session
    """
    try:
        success = conversation_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


async def analyze_conversation_context(session_id: str):
    """
    Background task to analyze conversation context
    """
    try:
        session = conversation_manager.get_session(session_id)
        if not session:
            return
        
        # Skip analysis for very short conversations
        if session.get_conversation_length() < 3:
            return
        
        config = await get_cached_config()
        ai_service = await get_ai_service(config)
        
        # Convert to ChatMessage format
        chat_history = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in session.messages
        ]
        
        # Analyze context
        analysis = await ai_service.analyze_conversation_context(chat_history)
        
        # Update session with analysis results
        conversation_manager.update_session_context(
            session_id=session_id,
            summary=analysis.get("context_summary", ""),
            topics=analysis.get("topics", []),
            sentiment=analysis.get("sentiment", "neutral")
        )
        
        logger.info(f"Context analysis completed for session: {session_id}")
        
    except Exception as e:
        logger.error(f"Error in background context analysis: {str(e)}")


@router.post("/conversations/cleanup")
async def cleanup_old_conversations(max_age_hours: int = 24):
    """
    Cleanup old inactive conversations
    """
    try:
        deleted_count = conversation_manager.cleanup_old_sessions(max_age_hours)
        return {
            "message": f"Cleanup completed successfully",
            "deleted_sessions": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error in conversation cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup conversations")