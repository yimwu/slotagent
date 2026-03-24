# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for MockLLM.
"""

import pytest

from slotagent.llm import LLMMessage, MockLLM


class TestMockLLMCreation:
    """Test MockLLM initialization"""

    def test_create_without_responses(self):
        """Test creating MockLLM without preset responses"""
        mock_llm = MockLLM()
        assert mock_llm is not None
        assert mock_llm.responses == {}
        assert mock_llm.call_history == []

    def test_create_with_responses(self):
        """Test creating MockLLM with preset responses"""
        responses = {
            "error": '{"analysis": "test", "fixed_params": {}}',
            "weather": '{"completed": true}',
        }
        mock_llm = MockLLM(responses=responses)
        assert mock_llm.responses == responses


class TestMockLLMComplete:
    """Test MockLLM complete method"""

    def test_complete_with_matching_response(self):
        """Test complete returns matching response"""
        mock_llm = MockLLM(
            responses={"error": '{"analysis": "fix it", "fixed_params": {}}'}
        )

        messages = [LLMMessage(role="user", content="Fix this error")]
        response = mock_llm.complete(messages)

        assert response.content == '{"analysis": "fix it", "fixed_params": {}}'
        assert response.model == "mock"

    def test_complete_with_no_matching_response(self):
        """Test complete returns default response when no match"""
        mock_llm = MockLLM(responses={"error": "error response"})

        messages = [LLMMessage(role="user", content="Hello")]
        response = mock_llm.complete(messages)

        assert response.content == "Mock response"
        assert response.model == "mock"

    def test_complete_records_call_history(self):
        """Test complete records call history"""
        mock_llm = MockLLM()

        messages1 = [LLMMessage(role="user", content="First call")]
        messages2 = [LLMMessage(role="user", content="Second call")]

        mock_llm.complete(messages1)
        mock_llm.complete(messages2)

        assert len(mock_llm.call_history) == 2
        assert mock_llm.call_history[0] == messages1
        assert mock_llm.call_history[1] == messages2

    def test_complete_ignores_temperature_and_max_tokens(self):
        """Test complete works with temperature and max_tokens"""
        mock_llm = MockLLM(responses={"test": "test response"})

        messages = [LLMMessage(role="user", content="test")]
        response = mock_llm.complete(messages, temperature=0.5, max_tokens=100)

        assert response.content == "test response"
