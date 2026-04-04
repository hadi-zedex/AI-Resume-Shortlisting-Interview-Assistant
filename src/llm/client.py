import time
import json
from openai import OpenAI
from openai import RateLimitError, APITimeoutError, APIConnectionError, APIStatusError
from typing import Optional
from src.config import config


class LLMClient:
    """
    Wrapper around the Groq client (OpenAI-compatible API).
    Handles retries, timeouts, and JSON extraction.
    All LLM calls in the codebase go through this class.
    """

    def __init__(self):
        if not config.GROQ_API_KEY:
            raise EnvironmentError("GROQ_API_KEY is not set.")
        self._client = OpenAI(
            api_key=config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = config.MAX_TOKENS,
    ) -> str:
        """
        Send a prompt to Claude and return the raw text response.
        Retries up to config.MAX_RETRIES times on transient failures.

        Args:
            prompt:     The user message / prompt.
            system:     Optional system prompt to set Claude's behaviour.
            max_tokens: Max tokens in the response.

        Returns:
            Raw string response from Claude.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        last_exception: Optional[Exception] = None

        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                response = self._client.chat.completions.create(
                    model=config.MODEL_NAME,
                    max_tokens=max_tokens,
                    messages=messages,
                )
                return response.choices[0].message.content

            except RateLimitError as e:
                wait = config.RETRY_DELAY_SECONDS * attempt
                print(f"[LLMClient] Rate limited. Waiting {wait}s (attempt {attempt}/{config.MAX_RETRIES})")
                time.sleep(wait)
                last_exception = e

            except APITimeoutError as e:
                wait = config.RETRY_DELAY_SECONDS * attempt
                print(f"[LLMClient] Timeout. Waiting {wait}s (attempt {attempt}/{config.MAX_RETRIES})")
                time.sleep(wait)
                last_exception = e

            except APIConnectionError as e:
                wait = config.RETRY_DELAY_SECONDS * attempt
                print(f"[LLMClient] Connection error. Waiting {wait}s (attempt {attempt}/{config.MAX_RETRIES})")
                time.sleep(wait)
                last_exception = e

            except APIStatusError as e:
                # Non-retryable (4xx errors like invalid request)
                raise RuntimeError(
                    f"[LLMClient] API error {e.status_code}: {e.message}"
                ) from e

        raise RuntimeError(
            f"[LLMClient] All {config.MAX_RETRIES} attempts failed. "
            f"Last error: {last_exception}"
        )

    def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = config.MAX_TOKENS,
    ) -> dict:
        """
        Same as complete() but parses and returns the response as a dict.
        Strips markdown code fences if Claude wraps the JSON in them.

        Args:
            prompt:     The user message / prompt.
            system:     Optional system prompt.
            max_tokens: Max tokens in the response.

        Returns:
            Parsed dict from Claude's JSON response.

        Raises:
            ValueError:  If the response cannot be parsed as JSON.
            RuntimeError: If all retries are exhausted.
        """
        raw = self.complete(prompt=prompt, system=system, max_tokens=max_tokens)
        return self._parse_json(raw)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """
        Strip markdown fences and parse JSON.
        Claude sometimes wraps JSON in ```json ... ``` even when told not to.
        """
        cleaned = raw.strip()

        # Strip ```json ... ``` or ``` ... ```
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"[LLMClient] Failed to parse Claude response as JSON.\n"
                f"Error: {e}\n"
                f"Raw response:\n{raw[:500]}..."  # Show first 500 chars for debugging
            ) from e


class _LazyLLMClient:
    """
    Lazy proxy for LLMClient.
    The real client is instantiated on first use so that importing this
    module does NOT raise EnvironmentError when GROQ_API_KEY is absent
    (e.g. during Streamlit Cloud module loading before secrets are injected).
    """

    def __init__(self):
        self._instance: Optional[LLMClient] = None

    def _get(self) -> LLMClient:
        if self._instance is None:
            self._instance = LLMClient()
        return self._instance

    def complete(self, *args, **kwargs) -> str:
        return self._get().complete(*args, **kwargs)

    def complete_json(self, *args, **kwargs) -> dict:
        return self._get().complete_json(*args, **kwargs)


# Singleton — import this everywhere
llm_client = _LazyLLMClient()