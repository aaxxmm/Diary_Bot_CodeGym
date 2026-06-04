
import logging
from typing import Optional
from openai import AsyncOpenAI
import httpx
from config import settings


logger = logging.getLogger(__name__)


class GPTService:
    """Service for OpenAI GPT chat completions"""

    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client if API key is available"""
        try:
            api_key = settings.openai_api_key

            if api_key and len(api_key) > 20:
                # HTTP клиент без прокси
                http_client = httpx.AsyncClient(
                    proxy=None,
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    follow_redirects=True
                )

                self.client = AsyncOpenAI(
                    api_key=api_key,
                    timeout=30.0,
                    max_retries=2,
                    http_client=http_client
                )
                logger.info("✅ OpenAI client initialized successfully")
            else:
                logger.warning("⚠️ OpenAI API key not found or invalid")

        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")

    async def get_response(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            max_tokens: int = 1000,
            temperature: float = 0.7
    ) -> Optional[str]:

        # ДИАГНОСТИКА
        logger.info(f"=== GPT ЗАПРОС ===")
        logger.info(f"API Key exists: {bool(self.client)}")
        logger.info(f"Prompt: {prompt[:100]}...")

        """Get response from GPT"""
        if not self.client:
            return "❌ OpenAI API не настроен. Пожалуйста, добавьте TOKEN_OPENAI в переменные окружения."

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            model = settings.openai_model if hasattr(settings, 'openai_model') else "gpt-3.5-turbo"

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            logger.info(f"✅ GPT ответ получен")
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            if "401" in str(e):
                return "❌ Неверный API ключ OpenAI. Проверьте TOKEN_OPENAI в настройках."
            return f"❌ Ошибка: {str(e)}"

    async def close(self):
        """Close HTTP client"""
        if self.client and hasattr(self.client, '_client'):
            await self.client._client.aclose()


# Singleton instance
gpt_service = GPTService()

async def transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
    """Транскрипция аудио через Whisper"""
    if not self.client:
        return None

    try:
        import io
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.ogg"

        transcript = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru",
            response_format="text"
        )

        return transcript if isinstance(transcript, str) else transcript.text

    except Exception as e:
        logger.error(f"Whisper error: {e}")
        return None


async def get_response_with_context(system_prompt: str, history: list, new_message: str) -> str:
    """Получить ответ от GPT с контекстом диалога"""
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": new_message}
        ]

        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"GPT ошибка: {e}")
        return f"❌ Ошибка: {str(e)}"