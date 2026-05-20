"""
Semuts.sh API Client
OpenAI-compatible client for Semuts.sh AI chat service.
"""
import httpx
import json
import logging
from typing import Optional, List, Dict, Any, Generator
from dataclasses import dataclass

logger = logging.getLogger("semuts_client")
logger.setLevel(logging.INFO)

SEMUTS_API_URL = "https://ai.semutssh.com/v1/chat/completions"
SEMUTS_MODELS_URL = "https://ai.semutssh.com/v1/models"


@dataclass
class SemutsConfig:
    api_key: str
    default_model: str = "gpt-4o-mini"
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: float = 30.0
    max_retries: int = 3


class SemutsError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class SemutsClient:
    def __init__(self, config: SemutsConfig):
        self.config = config
        self._client = httpx.Client(timeout=config.timeout)
        self._async_client = httpx.AsyncClient(timeout=config.timeout)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "model": model or self.config.default_model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": stream,
        }

    def _handle_error(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
            except:
                error_msg = response.text or "Unknown error"
            raise SemutsError(
                message=error_msg,
                status_code=response.status_code,
                details=error_data if "error_data" in dir() else None
            )

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat request and return the response.
        """
        payload = self._build_payload(messages, model, stream=False, **kwargs)
        retries = 0

        while retries <= self.config.max_retries:
            try:
                response = self._client.post(
                    SEMUTS_API_URL,
                    headers=self._get_headers(),
                    json=payload
                )
                self._handle_error(response)
                return response.json()
            except httpx.TimeoutException:
                retries += 1
                logger.warning(f"Timeout, retrying... ({retries}/{self.config.max_retries})")
                if retries > self.config.max_retries:
                    raise SemutsError("Request timeout after max retries")
            except SemutsError:
                raise
            except Exception as e:
                retries += 1
                logger.warning(f"Error: {e}, retrying... ({retries}/{self.config.max_retries})")
                if retries > self.config.max_retries:
                    raise SemutsError(str(e))

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async version of chat request.
        """
        payload = self._build_payload(messages, model, stream=False, **kwargs)
        retries = 0

        while retries <= self.config.max_retries:
            try:
                response = await self._async_client.post(
                    SEMUTS_API_URL,
                    headers=self._get_headers(),
                    json=payload
                )
                self._handle_error(response)
                return response.json()
            except httpx.TimeoutException:
                retries += 1
                logger.warning(f"Timeout, retrying... ({retries}/{self.config.max_retries})")
                if retries > self.config.max_retries:
                    raise SemutsError("Request timeout after max retries")
            except SemutsError:
                raise
            except Exception as e:
                retries += 1
                logger.warning(f"Error: {e}, retrying... ({retries}/{self.config.max_retries})")
                if retries > self.config.max_retries:
                    raise SemutsError(str(e))

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream chat response token by token.
        Returns generator yielding text chunks.
        """
        payload = self._build_payload(messages, model, stream=True, **kwargs)

        try:
            with self._client.stream(
                "POST",
                SEMUTS_API_URL,
                headers=self._get_headers(),
                json=payload
            ) as response:
                self._handle_error(response)
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise SemutsError(str(e))

    async def chat_stream_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Async streaming - returns async generator.
        Note: For FastAPI SSE, use chat_stream() with StreamingResponse instead.
        """
        payload = self._build_payload(messages, model, stream=True, **kwargs)

        try:
            async with self._async_client.stream(
                "POST",
                SEMUTS_API_URL,
                headers=self._get_headers(),
                json=payload
            ) as response:
                if response.status_code >= 400:
                    error_text = await response.aread()
                    raise SemutsError(error_text.decode(), response.status_code)
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Async streaming error: {e}")
            raise SemutsError(str(e))

    def get_models(self) -> List[Dict[str, Any]]:
        """
        List available models from Semuts.sh.
        """
        try:
            response = self._client.get(
                SEMUTS_MODELS_URL,
                headers=self._get_headers()
            )
            self._handle_error(response)
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            raise SemutsError(f"Failed to get models: {e}")

    async def get_models_async(self) -> List[Dict[str, Any]]:
        """
        Async version of get_models.
        """
        try:
            response = await self._async_client.get(
                SEMUTS_MODELS_URL,
                headers=self._get_headers()
            )
            self._handle_error(response)
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            raise SemutsError(f"Failed to get models: {e}")

    def test_streaming_support(self) -> bool:
        """
        Test if Semuts.sh supports streaming.
        Returns True if streaming works, False otherwise.
        """
        try:
            test_messages = [{"role": "user", "content": "Say 'test'"}]
            payload = self._build_payload(test_messages, stream=True)

            with self._client.stream(
                "POST",
                SEMUTS_API_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=10.0
            ) as response:
                if response.status_code >= 400:
                    return False
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            return True
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk:
                                return True
                        except:
                            continue
                return False
        except Exception as e:
            logger.warning(f"Streaming test failed: {e}")
            return False

    def close(self):
        self._client.close()

    async def close_async(self):
        await self._async_client.aclose()


def extract_content(response: Dict[str, Any]) -> str:
    """
    Helper to extract content from non-streaming response.
    """
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise SemutsError("Invalid response format")


def extract_usage(response: Dict[str, Any]) -> Dict[str, int]:
    """
    Helper to extract token usage from response.
    """
    try:
        return response.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    except:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}