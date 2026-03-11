import pytest
from unittest.mock import AsyncMock, patch
from backend.services.anthropic_service import ClaudeProvider
from backend.schemas import KandidaatProfiel

@pytest.mark.asyncio
async def test_claude_provider_generate_json():
    # Mock the anthropic client
    mock_client = AsyncMock()
    mock_messages = AsyncMock()
    mock_client.messages = mock_messages
    
    # Mock response
    mock_response = AsyncMock()
    mock_response.content = [AsyncMock(text='{"naam": "Test Jan", "kernrol": "Dev", "zijn": "Goed", "willen": "Meer", "kunnen": "Veel", "dossier_compleetheid": 100, "vervolgvragen": [], "stellingen": []}')]
    mock_messages.create.return_value = mock_response
    
    with patch('anthropic.AsyncAnthropic', return_value=mock_client):
        provider = ClaudeProvider(api_key="test_key")
        result = await provider.generate_json(
            model="claude-3-7-sonnet-latest",
            prompt="Test prompt",
            schema=KandidaatProfiel
        )
        
        assert result.naam == "Test Jan"
        assert result.kernrol == "Dev"
        mock_messages.create.assert_called_once()

@pytest.mark.asyncio
async def test_claude_provider_check_status_no_key():
    with patch('backend.config.ANTHROPIC_API_KEY', None):
        provider = ClaudeProvider(api_key=None)
        status = await provider.check_status()
        assert status["online"] is False
        assert "API Key ontbreekt" in status["error"]
