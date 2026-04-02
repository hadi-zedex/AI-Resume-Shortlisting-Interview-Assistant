import pytest
from unittest.mock import patch, MagicMock, call
import anthropic
from src.llm.client import LLMClient


@pytest.fixture
def client() -> LLMClient:
    """Create a fresh LLMClient for each test."""
    with patch(
        "src.llm.client.config.ANTHROPIC_API_KEY",
        "test-api-key-123",
    ):
        return LLMClient()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_mock_response(text: str = "Hello") -> MagicMock:
    """Build a fake Anthropic API response object."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=text)]
    return mock_response


def make_json_response(data: dict) -> MagicMock:
    """Build a fake Anthropic API response with JSON content."""
    import json
    return make_mock_response(json.dumps(data))


# ------------------------------------------------------------------
# Basic completion
# ------------------------------------------------------------------

class TestBasicCompletion:

    def test_complete_returns_string(self, client):
        """complete() should return a string."""
        with patch.object(
            client._client.messages,
            "create",
            return_value=make_mock_response("Test response"),
        ):
            result = client.complete("Test prompt")

        assert isinstance(result, str)
        assert result == "Test response"

    def test_complete_with_system_prompt(self, client):
        """complete() with system prompt should pass it to API."""
        mock_create = MagicMock(
            return_value=make_mock_response("Response")
        )
        with patch.object(client._client.messages, "create", mock_create):
            client.complete(
                prompt="User message",
                system="You are a helpful assistant.",
            )

        call_kwargs = mock_create.call_args.kwargs
        assert "system" in call_kwargs
        assert call_kwargs["system"] == "You are a helpful assistant."

    def test_complete_without_system_prompt(self, client):
        """complete() without system prompt should not pass system key."""
        mock_create = MagicMock(
            return_value=make_mock_response("Response")
        )
        with patch.object(client._client.messages, "create", mock_create):
            client.complete(prompt="User message")

        call_kwargs = mock_create.call_args.kwargs
        assert "system" not in call_kwargs

    def test_complete_uses_correct_model(self, client):
        """complete() should use the model from config."""
        from src.config import config

        mock_create = MagicMock(
            return_value=make_mock_response("Response")
        )
        with patch.object(client._client.messages, "create", mock_create):
            client.complete("Test prompt")

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["model"] == config.MODEL_NAME

    def test_complete_passes_max_tokens(self, client):
        """complete() should pass max_tokens to the API."""
        mock_create = MagicMock(
            return_value=make_mock_response("Response")
        )
        with patch.object(client._client.messages, "create", mock_create):
            client.complete("Test prompt", max_tokens=500)

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 500


# ------------------------------------------------------------------
# JSON completion
# ------------------------------------------------------------------

class TestJSONCompletion:

    def test_complete_json_returns_dict(self, client):
        """complete_json() should return a parsed dict."""
        with patch.object(
            client._client.messages,
            "create",
            return_value=make_json_response({"score": 75}),
        ):
            result = client.complete_json("Test prompt")

        assert isinstance(result, dict)
        assert result["score"] == 75

    def test_complete_json_strips_markdown_fences(self, client):
        """
        complete_json() should handle Claude wrapping
        JSON in markdown code fences.
        """
        fenced_response = make_mock_response(
            "```json\n{\"score\": 80}\n```"
        )
        with patch.object(
            client._client.messages,
            "create",
            return_value=fenced_response,
        ):
            result = client.complete_json("Test prompt")

        assert result["score"] == 80

    def test_complete_json_strips_plain_fences(self, client):
        """
        complete_json() should handle ``` fences
        without json language tag.
        """
        fenced_response = make_mock_response(
            "```\n{\"key\": \"value\"}\n```"
        )
        with patch.object(
            client._client.messages,
            "create",
            return_value=fenced_response,
        ):
            result = client.complete_json("Test prompt")

        assert result["key"] == "value"

    def test_complete_json_raises_on_invalid_json(self, client):
        """
        complete_json() should raise ValueError when
        Claude returns non-JSON text.
        """
        with patch.object(
            client._client.messages,
            "create",
            return_value=make_mock_response("This is not JSON at all."),
        ):
            with pytest.raises(ValueError, match="Failed to parse"):
                client.complete_json("Test prompt")

    def test_complete_json_error_includes_raw_response(self, client):
        """
        ValueError from bad JSON should include a snippet
        of the raw response for debugging.
        """
        with patch.object(
            client._client.messages,
            "create",
            return_value=make_mock_response("Not JSON content here"),
        ):
            with pytest.raises(ValueError) as exc_info:
                client.complete_json("Test prompt")

        assert "Not JSON" in str(exc_info.value) or \
               "Raw response" in str(exc_info.value)


# ------------------------------------------------------------------
# Retry logic — rate limit
# ------------------------------------------------------------------

class TestRetryOnRateLimit:

    def test_retries_on_rate_limit_error(self, client):
        """
        Client should retry up to MAX_RETRIES times
        on RateLimitError before succeeding.
        """
        from src.config import config

        success_response = make_mock_response("Success after retry")
        mock_create = MagicMock(
            side_effect=[
                anthropic.RateLimitError(
                    message="Rate limited",
                    response=MagicMock(status_code=429),
                    body={},
                ),
                success_response,
            ]
        )

        with patch.object(client._client.messages, "create", mock_create), \
             patch("src.llm.client.time.sleep"):
            result = client.complete("Test prompt")

        assert result == "Success after retry"
        assert mock_create.call_count == 2

    def test_raises_after_all_retries_exhausted(self, client):
        """
        Client should raise RuntimeError after all
        MAX_RETRIES attempts fail with RateLimitError.
        """
        from src.config import config

        mock_create = MagicMock(
            side_effect=anthropic.RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body={},
            )
        )

        with patch.object(client._client.messages, "create", mock_create), \
             patch("src.llm.client.time.sleep"):
            with pytest.raises(RuntimeError, match="attempts failed"):
                client.complete("Test prompt")

        assert mock_create.call_count == config.MAX_RETRIES

    def test_sleep_called_between_retries(self, client):
        """
        time.sleep should be called between retries
        with increasing delay.
        """
        mock_create = MagicMock(
            side_effect=[
                anthropic.RateLimitError(
                    message="Rate limited",
                    response=MagicMock(status_code=429),
                    body={},
                ),
                anthropic.RateLimitError(
                    message="Rate limited",
                    response=MagicMock(status_code=429),
                    body={},
                ),
                make_mock_response("Success"),
            ]
        )

        with patch.object(client._client.messages, "create", mock_create), \
             patch("src.llm.client.time.sleep") as mock_sleep:
            client.complete("Test prompt")

        # Sleep should be called twice (after attempt 1 and 2)
        assert mock_sleep.call_count == 2

        # Delay should increase each retry
        delays = [c.args[0] for c in mock_sleep.call_args_list]
        assert delays[0] < delays[1]


# ------------------------------------------------------------------
# Retry logic — timeout
# ------------------------------------------------------------------

class TestRetryOnTimeout:

    def test_retries_on_timeout_error(self, client):
        """Client should retry on APITimeoutError."""
        mock_create = MagicMock(
            side_effect=[
                anthropic.APITimeoutError(request=MagicMock()),
                make_mock_response("Success after timeout"),
            ]
        )

        with patch.object(client._client.messages, "create", mock_create), \
             patch("src.llm.client.time.sleep"):
            result = client.complete("Test prompt")

        assert result == "Success after timeout"
        assert mock_create.call_count == 2

    def test_retries_on_connection_error(self, client):
        """Client should retry on APIConnectionError."""
        mock_create = MagicMock(
            side_effect=[
                anthropic.APIConnectionError(request=MagicMock()),
                make_mock_response("Success after connection error"),
            ]
        )

        with patch.object(client._client.messages, "create", mock_create), \
             patch("src.llm.client.time.sleep"):
            result = client.complete("Test prompt")

        assert result == "Success after connection error"


# ------------------------------------------------------------------
# Non-retryable errors
# ------------------------------------------------------------------

class TestNonRetryableErrors:

    def test_api_status_error_not_retried(self, client):
        """
        APIStatusError (4xx) should fail immediately
        without retrying.
        """
        mock_create = MagicMock(
            side_effect=anthropic.APIStatusError(
                message="Bad request",
                response=MagicMock(status_code=400),
                body={},
            )
        )

        with patch.object(client._client.messages, "create", mock_create), \
             patch("src.llm.client.time.sleep"):
            with pytest.raises(RuntimeError, match="400"):
                client.complete("Test prompt")

        # Should only be called once — no retries
        assert mock_create.call_count == 1

    def test_runtime_error_message_includes_status_code(self, client):
        """RuntimeError from 4xx should include the status code."""
        mock_create = MagicMock(
            side_effect=anthropic.APIStatusError(
                message="Unauthorized",
                response=MagicMock(status_code=401),
                body={},
            )
        )

        with patch.object(client._client.messages, "create", mock_create), \
             patch("src.llm.client.time.sleep"):
            with pytest.raises(RuntimeError) as exc_info:
                client.complete("Test prompt")

        assert "401" in str(exc_info.value)


# ------------------------------------------------------------------
# Missing API key
# ------------------------------------------------------------------

class TestMissingAPIKey:

    def test_missing_api_key_raises_on_init(self):
        """
        LLMClient should raise EnvironmentError
        if API key is not set.
        """
        with patch(
            "src.llm.client.config.ANTHROPIC_API_KEY", ""
        ):
            with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
                LLMClient()


# ------------------------------------------------------------------
# JSON parse helper
# ------------------------------------------------------------------

class TestParseJSON:

    def test_parse_clean_json(self, client):
        """_parse_json should parse clean JSON strings."""
        result = client._parse_json('{"key": "value", "number": 42}')

        assert result["key"] == "value"
        assert result["number"] == 42

    def test_parse_json_with_fences(self, client):
        """_parse_json should strip markdown fences."""
        result = client._parse_json('```json\n{"key": "value"}\n```')

        assert result["key"] == "value"

    def test_parse_json_with_whitespace(self, client):
        """_parse_json should handle leading/trailing whitespace."""
        result = client._parse_json('  \n  {"key": "value"}  \n  ')

        assert result["key"] == "value"

    def test_parse_invalid_json_raises_value_error(self, client):
        """_parse_json should raise ValueError on invalid JSON."""
        with pytest.raises(ValueError, match="Failed to parse"):
            client._parse_json("not valid json {{}}")

    def test_parse_nested_json(self, client):
        """_parse_json should handle nested JSON structures."""
        raw = '{"scores": {"exact": 80, "semantic": 70}}'
        result = client._parse_json(raw)

        assert result["scores"]["exact"] == 80