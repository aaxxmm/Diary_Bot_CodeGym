
"""OpenAI GPT service for chat completions"""
import logging
from typing import Optional
from openai import AsyncOpenAI
import config
import os
import httpx

logger = logging.getLogger(__name__)


class GPTService:
    """Service for OpenAI GPT chat completions"""

    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client if API key is available"""
        try:
            # Получаем API ключ из config
            api_key = getattr(config, 'token_openai', None)

            if not api_key:
                api_key = getattr(config, 'OPENAI_API_KEY', None)

            # Проверяем ключ
            if api_key and len(api_key) > 20 and api_key.startswith('sk-'):
                # СОЗДАЕМ КАСТОМНЫЙ HTTPX КЛИЕНТ БЕЗ ПРОКСИ
                # Это ключевое решение проблемы!
                http_client = httpx.AsyncClient(
                    proxy=None,  # Явно отключаем прокси
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    follow_redirects=True,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                )

                # Создаем клиент OpenAI с нашим HTTP клиентом
                self.client = AsyncOpenAI(
                    api_key=api_key,
                    timeout=30.0,
                    max_retries=2,
                    http_client=http_client
                )
                logger.info("✅ OpenAI client initialized successfully (proxy disabled)")
            else:
                logger.warning(f"❌ OpenAI API key invalid. Key: {api_key[:15] if api_key else 'None'}...")

        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")

    async def get_response(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            max_tokens: int = 500,
            temperature: float = 0.7
    ) -> Optional[str]:
        """Get response from GPT"""
        if not self.client:
            return "❌ OpenAI API не настроен. Пожалуйста, добавьте TOKEN_OPENAI в .env файл."

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            model = getattr(config, 'OPENAI_MODEL', 'gpt-3.5-turbo')

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Проверяем статус 401 - неверный ключ
            if "401" in str(e):
                return "❌ Неверный API ключ OpenAI. Проверьте TOKEN_OPENAI в .env файле"
            return f"❌ Ошибка: {str(e)}"

    async def close(self):
        """Закрыть HTTP клиент"""
        if self.client and hasattr(self.client, '_client'):
            await self.client._client.aclose()


# Singleton instance
gpt_service = GPTService()