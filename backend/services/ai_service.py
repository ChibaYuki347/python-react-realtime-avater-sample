"""
AI Service for GPT-4.1 integration and response generation
"""
import os
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: Optional[str] = None


class AIResponse(BaseModel):
    """AI response model"""
    content: str
    model_used: str
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None
    conversation_id: Optional[str] = None


class AIService:
    """Azure OpenAI GPT-4.1 service for generating AI responses"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AI Service with Azure OpenAI GPT-4.1
        
        Args:
            config: Configuration dictionary containing API keys and endpoints
        """
        self.config = config
        self.api_key = config.get("openai_api_key")
        self.endpoint = config.get("openai_endpoint")
        self.api_version = config.get("openai_api_version", "2024-10-21")
        self.deployment_name = config.get("openai_deployment_name", "gpt-4-1")
        self.use_mock = config.get("use_mock_ai", False)
        
        if self.use_mock:
            logger.info("AI Service initialized in MOCK mode for development")
            self.client = None
            return
        
        if not self.endpoint:
            raise ValueError("OpenAI endpoint is required")
        
        # Use Azure AD authentication if no API key provided (development mode)
        if self.api_key:
            # Use API key authentication
            self.client = AsyncAzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.endpoint
            )
            logger.info("Initialized AI Service with API key authentication")
        else:
            # Use Azure AD authentication (DefaultAzureCredential)
            from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
            
            async def get_token():
                credential = AsyncDefaultAzureCredential()
                token = await credential.get_token("https://cognitiveservices.azure.com/.default")
                return token.token
            
            self.client = AsyncAzureOpenAI(
                azure_ad_token_provider=get_token,
                api_version=self.api_version,
                azure_endpoint=self.endpoint
            )
            logger.info("Initialized AI Service with Azure AD authentication")
        
        logger.info(f"AI Service configured with GPT-4.1 deployment: {self.deployment_name}")
    
    async def generate_response(
        self, 
        user_message: str, 
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> AIResponse:
        """
        Generate AI response using GPT-4.1
        
        Args:
            user_message: User's input message
            conversation_history: Previous conversation messages
            system_prompt: Custom system prompt
            max_tokens: Maximum tokens for response
            temperature: Response creativity (0.0-1.0)
            
        Returns:
            AI response object
        """
        import time
        start_time = time.time()
        
        try:
            # Mock AI response for development
            if self.use_mock:
                import asyncio
                await asyncio.sleep(1)  # Simulate API call delay
                
                mock_responses = [
                    f"こんにちは！あなたの質問「{user_message}」にお答えします。これはモック応答です。",
                    f"興味深いご質問ですね。「{user_message}」について説明します。実際のAIサービスが利用可能になると、より詳細な応答を提供できます。",
                    f"ありがとうございます！「{user_message}」に関して、開発環境でのテスト応答をお返しします。",
                    "日本語での自然な会話をテストしています。実際のGPT-4.1が接続されると、より高度な応答が可能になります。"
                ]
                
                response_content = mock_responses[len(user_message) % len(mock_responses)]
                
                return AIResponse(
                    content=response_content,
                    model_used="mock-gpt-4.1",
                    tokens_used=len(response_content),
                    response_time=time.time() - start_time,
                    conversation_id=None
                )
            
            # Build messages array
            messages = []
            
            # Add system prompt
            default_system_prompt = """あなたは親しみやすく、知識豊富なAIアシスタントです。
ユーザーとの対話を通じて、有用で正確な情報を提供し、質問に丁寧に答えます。
日本語で自然で流暢な回答を心がけてください。
必要に応じて、専門的な内容も分かりやすく説明します。"""
            
            messages.append({
                "role": "system",
                "content": system_prompt or default_system_prompt
            })
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-10:]:  # Keep last 10 messages for context
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Call GPT-4.1
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract response
            if response.choices and len(response.choices) > 0:
                ai_content = response.choices[0].message.content or "応答が生成されませんでした。"
            else:
                ai_content = "応答が生成されませんでした。"
                
            tokens_used = response.usage.total_tokens if response.usage else None
            response_time = time.time() - start_time
            
            logger.info(f"GPT-4.1 response generated in {response_time:.2f}s, tokens: {tokens_used}")
            
            return AIResponse(
                content=ai_content,
                model_used=self.deployment_name,
                tokens_used=tokens_used,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            raise
    
    async def generate_streaming_response(
        self, 
        user_message: str, 
        conversation_history: List[ChatMessage] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming AI response using GPT-4.1
        
        Args:
            user_message: User's input message
            conversation_history: Previous conversation messages
            system_prompt: Custom system prompt
            max_tokens: Maximum tokens for response
            temperature: Response creativity (0.0-1.0)
            
        Yields:
            Streaming response chunks
        """
        try:
            # Mock streaming response for development
            if self.use_mock:
                import asyncio
                
                mock_response = f"こんにちは！ストリーミング応答のテストです。「{user_message}」についてお答えします。"
                words = mock_response.split()
                
                for word in words:
                    yield f"data: {json.dumps({'content': word + ' '}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.1)  # Simulate streaming delay
                
                yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
                return
            
            # Build messages array (same as generate_response)
            messages = []
            
            default_system_prompt = """あなたは親しみやすく、知識豊富なAIアシスタントです。
ユーザーとの対話を通じて、有用で正確な情報を提供し、質問に丁寧に答えます。
日本語で自然で流暢な回答を心がけてください。
必要に応じて、専門的な内容も分かりやすく説明します。"""
            
            messages.append({
                "role": "system",
                "content": system_prompt or default_system_prompt
            })
            
            if conversation_history:
                for msg in conversation_history[-10:]:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Call GPT-4.1 with streaming
            stream = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            
            async for chunk in stream:
                # 安全にchunkの内容をチェック
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if hasattr(choice, 'delta') and hasattr(choice.delta, 'content'):
                        content = choice.delta.content
                        if content is not None:
                            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            
            # ストリーミング完了を通知
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"Error generating streaming response: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            # エラー時にもストリーミング形式でエラーを返す
            yield f"data: {json.dumps({'error': f'申し訳ありません。エラーが発生しました: {str(e)}'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        finally:
            # リソースのクリーンアップ
            try:
                if hasattr(self.client, '_client') and hasattr(self.client._client, 'close'):
                    await self.client._client.close()
            except Exception as cleanup_error:
                logger.warning(f"Client cleanup warning: {str(cleanup_error)}")
    
    async def analyze_conversation_context(
        self, 
        conversation_history: List[ChatMessage]
    ) -> Dict[str, Any]:
        """
        Analyze conversation context to extract key topics and sentiment
        
        Args:
            conversation_history: List of conversation messages
            
        Returns:
            Analysis results including topics, sentiment, etc.
        """
        try:
            if not conversation_history:
                return {"topics": [], "sentiment": "neutral", "context_summary": ""}
            
            # Create analysis prompt
            conversation_text = "\n".join([
                f"{msg.role}: {msg.content}" 
                for msg in conversation_history[-20:]  # Analyze last 20 messages
            ])
            
            analysis_prompt = f"""以下の会話を分析してください：

{conversation_text}

以下の情報をJSON形式で返してください：
- topics: 主要なトピックのリスト (最大5個)
- sentiment: 全体的な感情 ("positive", "negative", "neutral")
- context_summary: 会話の要約 (100文字以内)
- user_intent: ユーザーの意図や目的

回答は有効なJSONのみで返してください。"""

            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=500,
                temperature=0.1
            )
            
            # Parse JSON response
            analysis_result = json.loads(response.choices[0].message.content)
            logger.info("Conversation context analysis completed")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing conversation context: {str(e)}")
            return {
                "topics": [],
                "sentiment": "neutral",
                "context_summary": "",
                "user_intent": "unknown"
            }


# Global AI service instance
ai_service: Optional[AIService] = None


async def get_ai_service(config: Dict[str, Any]) -> AIService:
    """Get or create the global AI service instance"""
    global ai_service
    if ai_service is None:
        ai_service = AIService(config)
    return ai_service