"""
Enhanced ConversationAgent with streaming support and improved system prompts.
Implements "Compassionate Caretaker" persona with safety guardrails.

Includes VRAM management for concurrent image/document processing safety.
"""

import logging
from typing import Optional, AsyncGenerator, Dict, Any
import os

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from groq import Groq
except ImportError:
    Groq = None

from config.prompts import (
    SYSTEM_PROMPT, 
    EMERGENCY_KEYWORDS, 
    MEDICAL_DISCLAIMER,
    ERROR_RESPONSES
)
from middleware.security_utils import security_validator, DataProtection
from services.vram_manager import get_vram_manager

logger = logging.getLogger(__name__)

class EnhancedConversationAgent:
    """
    Enhanced conversation handler with streaming, safety checks, and system prompts.
    Supports multiple LLM providers (Anthropic, Groq, OpenAI).
    """
    
    def __init__(self):
        self.provider = self._detect_provider()
        self.client = self._initialize_client()
        self.model = self._get_model()
        self.system_prompt = SYSTEM_PROMPT
        self.conversation_history = []
        
    def _detect_provider(self) -> str:
        """Detect which LLM provider to use based on environment variables"""
        if os.getenv('GROQ_API_KEY'):
            return 'groq'
        elif os.getenv('OPENAI_API_KEY'):
            return 'openai'
        elif os.getenv('ANTHROPIC_API_KEY'):
            return 'anthropic'
        else:
            logger.warning("No LLM API key configured. Using local Ollama.")
            return 'ollama'
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        if self.provider == 'groq' and Groq:
            return Groq(api_key=os.getenv('GROQ_API_KEY'))
        elif self.provider == 'anthropic' and anthropic:
            return anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        elif self.provider == 'openai':
            # OpenAI client initialization
            try:
                from openai import OpenAI
                return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            except:
                return None
        else:
            return None
    
    def _get_model(self) -> str:
        """Get the appropriate model name based on provider"""
        if self.provider == 'groq':
            return 'mixtral-8x7b-32768'
        elif self.provider == 'openai':
            return 'gpt-4-turbo'
        elif self.provider == 'anthropic':
            return 'claude-3-sonnet-20240229'
        else:
            return 'neural-chat'  # Ollama default
    
    def _is_emergency(self, user_input: str) -> bool:
        """Detect if query contains emergency indicators"""
        user_input_lower = user_input.lower()
        return any(keyword in user_input_lower for keyword in EMERGENCY_KEYWORDS)
    
    def _build_emergency_response(self, user_input: str) -> str:
        """Generate urgent response for emergency cases"""
        return """🚨 **EMERGENCY DETECTED** 🚨

Your query suggests a medical emergency. 

**IMMEDIATE ACTION REQUIRED:**
1. **Call Emergency Services:** 
   - India: 112 or 108 (Ambulance)
   - International: +91-112 or local equivalent
2. **Go to Nearest ER:** Do not wait for online consultation
3. **Inform Medical Staff:** Tell them about your symptoms

**I can help with:** After you've received emergency care, I can help find specialized hospitals for follow-up treatment.

Your health is the priority. Please seek immediate professional help now.
"""
    
    async def chat(self, user_input: str, conversation_context: Optional[Dict] = None,
                   stream: bool = True, request_type: str = "text") -> AsyncGenerator[str, None] if stream else str:
        """
        Process user message and generate response with optional streaming.
        
        Args:
            user_input: User's message
            conversation_context: Previous conversation history and metadata
            stream: Whether to stream response token-by-token
            request_type: Type of request ('text', 'image', 'document') for VRAM management
            
        Returns:
            AsyncGenerator yielding response chunks (if stream=True) or full response string
        """
        
        # Security validation
        is_valid, error_msg = security_validator.validate_user_input(user_input)
        if not is_valid:
            yield f"⚠️ {error_msg}"
            return
        
        # Emergency check
        if self._is_emergency(user_input):
            yield self._build_emergency_response(user_input)
            return
        
        # VRAM management for image/document processing
        vram_manager = get_vram_manager()
        
        # Try to acquire VRAM slot (with longer timeout for image analysis)
        slot_timeout = 300.0 if request_type in ['image', 'document'] else 60.0
        
        if not await vram_manager.acquire_slot(timeout_sec=slot_timeout):
            logger.warning(
                f"VRAM slot acquisition timeout for {request_type} request. "
                f"Current load: {vram_manager.get_stats()}"
            )
            yield (
                "🔄 **System Under High Load**\n\n"
                "We're processing many requests right now. Please wait a moment and try again.\n"
                "Updates are queued in order.\n\n"
                f"Queue status: {vram_manager.get_stats()['current_active']}/{vram_manager.get_stats()['max_slots']} active"
            )
            return
        
        try:
            # Add to conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': user_input
            })
            
            if stream and self.provider != 'ollama':
                async for chunk in self._stream_response(user_input):
                    yield chunk
            else:
                response = await self._get_response(user_input)
                yield response
                
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            yield ERROR_RESPONSES.get('model_timeout', 'An error occurred. Please try again.')
        finally:
            # Always release VRAM slot
            vram_manager.release_slot()
            logger.info(
                f"Slot released | Remaining active: {vram_manager.get_stats()['current_active']} | "
                f"Total processed: {vram_manager.get_stats()['total_requests']}"
            )
    
    async def _stream_response(self, user_input: str) -> AsyncGenerator[str, None]:
        """Stream response tokens from LLM"""
        
        if self.provider == 'groq' and self.client:
            try:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    system=self.system_prompt,
                    temperature=0.7,
                    max_tokens=1024,
                    stream=True,
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
            except Exception as e:
                logger.error(f"Groq streaming error: {str(e)}")
                yield ERROR_RESPONSES['model_timeout']
        
        elif self.provider == 'anthropic' and self.client:
            try:
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=1024,
                    system=self.system_prompt,
                    messages=self.conversation_history,
                ) as stream:
                    for text in stream.text_stream:
                        yield text
                        
            except Exception as e:
                logger.error(f"Anthropic streaming error: {str(e)}")
                yield ERROR_RESPONSES['model_timeout']
    
    async def _get_response(self, user_input: str) -> str:
        """Get non-streaming response from LLM"""
        
        try:
            if self.provider == 'groq' and self.client:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    system=self.system_prompt,
                    temperature=0.7,
                    max_tokens=1024,
                )
                return response.choices[0].message.content
            
            elif self.provider == 'anthropic' and self.client:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=self.system_prompt,
                    messages=self.conversation_history,
                )
                return response.content[0].text
            
            else:
                # Fallback to local Ollama
                return await self._get_ollama_response(user_input)
                
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            return ERROR_RESPONSES['model_timeout']
    
    async def _get_ollama_response(self, user_input: str) -> str:
        """Fallback to local Ollama model"""
        import urllib.request
        import json
        
        try:
            url = "http://localhost:11434/api/generate"
            data = {
                'model': 'neural-chat',
                'prompt': f"System: {self.system_prompt}\n\nUser: {user_input}",
                'stream': False
            }
            
            req = urllib.request.Request(url, data=json.dumps(data).encode(), 
                                        headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                return result.get('response', ERROR_RESPONSES['model_timeout'])
                
        except Exception as e:
            logger.error(f"Ollama error: {str(e)}")
            return ERROR_RESPONSES['model_timeout']
    
    def add_disclaimer(self, response: str) -> str:
        """Add safety disclaimer to medical responses"""
        if any(keyword in response.lower() for keyword in 
               ['symptom', 'disease', 'condition', 'treatment', 'diagnosis']):
            return response + MEDICAL_DISCLAIMER
        return response

# Global agent instance
enhanced_agent = None

def get_agent() -> EnhancedConversationAgent:
    """Get or initialize the conversation agent (singleton pattern)"""
    global enhanced_agent
    if enhanced_agent is None:
        enhanced_agent = EnhancedConversationAgent()
    return enhanced_agent
