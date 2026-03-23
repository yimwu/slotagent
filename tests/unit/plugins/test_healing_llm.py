# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for HealingLLM plugin.
"""

import json
import time

import pytest

from slotagent.llm import LLMMessage, MockLLM
from slotagent.plugins.healing import HealingLLM
from slotagent.types import PluginContext, PluginResult


class TestHealingLLMCreation:
    """Test HealingLLM initialization"""

    def test_create_with_llm(self):
        """Test creating HealingLLM with LLM instance"""
        mock_llm = MockLLM()
        plugin = HealingLLM(llm=mock_llm)

        assert plugin.llm is mock_llm
        assert plugin.max_retries == 2
        assert plugin.temperature == 0.3

    def test_create_with_custom_params(self):
        """Test creating HealingLLM with custom parameters"""
        mock_llm = MockLLM()
        plugin = HealingLLM(llm=mock_llm, max_retries=5, temperature=0.5)

        assert plugin.max_retries == 5
        assert plugin.temperature == 0.5

    def test_validate_returns_true_with_llm(self):
        """Test validate returns True when LLM is present"""
        mock_llm = MockLLM()
        plugin = HealingLLM(llm=mock_llm)

        assert plugin.validate() is True

    def test_validate_returns_false_without_llm(self):
        """Test validate returns False when LLM is None"""
        plugin = HealingLLM(llm=None)

        assert plugin.validate() is False


class TestHealingLLMExecute:
    """Test HealingLLM execute method"""

    def test_no_error_to_heal(self):
        """Test healing when there's no error"""
        mock_llm = MockLLM()
        plugin = HealingLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test Tool",
            tool_description="A test tool",
            params={"param": "value"},
            layer="healing",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={},  # No error
        )

        result = plugin.execute(context)

        assert result.success is True
        assert result.data["recovered"] is False
        assert result.data["reason"] == "No error to heal"

    def test_successful_parameter_fix(self):
        """Test successful parameter fixing by LLM"""
        # Preset LLM response
        fixed_response = json.dumps(
            {
                "analysis": "参数location拼写错误,应该是Beijing而不是Beiing",
                "fixed_params": {"location": "Beijing"},
            }
        )

        mock_llm = MockLLM(responses={"执行错误": fixed_response})
        plugin = HealingLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="weather_query",
            tool_name="天气查询",
            tool_description="获取指定城市的天气信息",
            params={"location": "Beiing"},
            layer="healing",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"error": "City not found: Beiing"},
        )

        result = plugin.execute(context)

        assert result.success is True
        assert result.should_continue is True
        assert result.data["recovered"] is True
        assert result.data["fixed_params"] == {"location": "Beijing"}
        assert "拼写错误" in result.data["analysis"]

    def test_llm_response_with_extra_text(self):
        """Test parsing LLM response when it contains extra text"""
        # LLM response with explanation text
        response_with_text = """
        我来分析这个错误:

        {"analysis": "参数错误", "fixed_params": {"city": "Beijing"}}

        希望这个修复能解决问题!
        """

        mock_llm = MockLLM(responses={"执行错误": response_with_text})
        plugin = HealingLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test tool",
            params={"city": "Beiing"},
            layer="healing",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"error": "City not found"},
        )

        result = plugin.execute(context)

        assert result.success is True
        assert result.data["recovered"] is True
        assert result.data["fixed_params"] == {"city": "Beijing"}

    def test_llm_cannot_fix_parameters(self):
        """Test when LLM cannot fix parameters"""
        # LLM response without fixed_params
        response = json.dumps({"analysis": "无法修复此错误", "fixed_params": None})

        mock_llm = MockLLM(responses={"error": response})
        plugin = HealingLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test",
            params={"param": "value"},
            layer="healing",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"error": "Unrecoverable error"},
        )

        result = plugin.execute(context)

        assert result.success is False
        assert result.data["recovered"] is False
        assert "LLM无法修复参数" in result.data["reason"]

    def test_llm_returns_invalid_json(self):
        """Test error handling when LLM returns invalid JSON"""
        mock_llm = MockLLM(responses={"error": "This is not valid JSON"})
        plugin = HealingLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test",
            params={"param": "value"},
            layer="healing",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"error": "Some error"},
        )

        result = plugin.execute(context)

        assert result.success is False
        assert result.data["recovered"] is False
        assert "响应解析失败" in result.error

    def test_llm_call_raises_exception(self):
        """Test error handling when LLM call raises exception"""

        class FailingLLM:
            def complete(self, messages, temperature=0.7, max_tokens=None):
                raise RuntimeError("LLM service unavailable")

        plugin = HealingLLM(llm=FailingLLM())

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test",
            params={"param": "value"},
            layer="healing",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"error": "Some error"},
        )

        result = plugin.execute(context)

        assert result.success is False
        assert result.data["recovered"] is False
        assert "LLM调用失败" in result.error
        assert "LLM service unavailable" in result.error
