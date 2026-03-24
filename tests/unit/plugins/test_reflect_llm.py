# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for ReflectLLM plugin.
"""

import json
import time

import pytest

from slotagent.llm import LLMMessage, MockLLM
from slotagent.plugins.reflect import ReflectLLM
from slotagent.types import PluginContext, PluginResult


class TestReflectLLMCreation:
    """Test ReflectLLM initialization"""

    def test_create_with_llm(self):
        """Test creating ReflectLLM with LLM instance"""
        mock_llm = MockLLM()
        plugin = ReflectLLM(llm=mock_llm)

        assert plugin.llm is mock_llm
        assert plugin.temperature == 0.2
        assert plugin.min_quality_score == 60

    def test_create_with_custom_params(self):
        """Test creating ReflectLLM with custom parameters"""
        mock_llm = MockLLM()
        plugin = ReflectLLM(llm=mock_llm, temperature=0.5, min_quality_score=80)

        assert plugin.temperature == 0.5
        assert plugin.min_quality_score == 80

    def test_validate_returns_true_with_llm(self):
        """Test validate returns True when LLM is present"""
        mock_llm = MockLLM()
        plugin = ReflectLLM(llm=mock_llm)

        assert plugin.validate() is True

    def test_validate_returns_false_without_llm(self):
        """Test validate returns False when LLM is None"""
        plugin = ReflectLLM(llm=None)

        assert plugin.validate() is False


class TestReflectLLMExecute:
    """Test ReflectLLM execute method"""

    def test_no_result_to_reflect(self):
        """Test reflection when there's no result"""
        mock_llm = MockLLM()
        plugin = ReflectLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test Tool",
            tool_description="A test tool",
            params={"param": "value"},
            layer="reflect",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={},  # No result
        )

        result = plugin.execute(context)

        assert result.success is True
        assert result.data["task_completed"] is False
        assert result.data["reason"] == "无执行结果"

    def test_successful_reflection_task_completed(self):
        """Test successful reflection when task is completed"""
        # Preset LLM response
        reflect_response = json.dumps(
            {
                "completed": True,
                "reason": "结果包含所需的天气信息",
                "quality_score": 95,
            }
        )

        mock_llm = MockLLM(responses={"请判断": reflect_response})
        plugin = ReflectLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="weather_query",
            tool_name="天气查询",
            tool_description="获取指定城市的天气信息",
            params={"location": "Beijing"},
            layer="reflect",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"result": {"temperature": 20, "condition": "sunny"}},
        )

        result = plugin.execute(context)

        assert result.success is True
        assert result.data["task_completed"] is True
        assert result.data["quality_score"] == 95
        assert "天气信息" in result.data["reason"]

    def test_task_not_completed(self):
        """Test reflection when task is not completed"""
        reflect_response = json.dumps(
            {
                "completed": False,
                "reason": "结果缺少必要的字段",
                "quality_score": 40,
            }
        )

        mock_llm = MockLLM(responses={"请判断": reflect_response})
        plugin = ReflectLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test tool",
            params={"param": "value"},
            layer="reflect",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"result": {"incomplete": "data"}},
        )

        result = plugin.execute(context)

        assert result.success is True
        assert result.data["task_completed"] is False
        assert result.data["quality_score"] == 40

    def test_low_quality_score_marks_incomplete(self):
        """Test that low quality score marks task as incomplete"""
        reflect_response = json.dumps(
            {
                "completed": True,  # LLM says completed
                "reason": "结果质量较低",
                "quality_score": 50,  # But quality is below threshold (60)
            }
        )

        mock_llm = MockLLM(responses={"请判断": reflect_response})
        plugin = ReflectLLM(llm=mock_llm, min_quality_score=60)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test",
            params={},
            layer="reflect",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"result": {"data": "low quality"}},
        )

        result = plugin.execute(context)

        assert result.success is True
        assert result.data["task_completed"] is False  # Quality too low
        assert result.data["quality_score"] == 50

    def test_llm_response_with_extra_text(self):
        """Test parsing LLM response when it contains extra text"""
        response_with_text = """
        让我来评估这个结果:

        {"completed": true, "reason": "结果完整", "quality_score": 90}

        总体来说质量不错!
        """

        mock_llm = MockLLM(responses={"请判断": response_with_text})
        plugin = ReflectLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test",
            params={},
            layer="reflect",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"result": {"data": "complete"}},
        )

        result = plugin.execute(context)

        assert result.success is True
        assert result.data["task_completed"] is True
        assert result.data["quality_score"] == 90

    def test_llm_returns_invalid_json_defaults_to_completed(self):
        """Test that invalid JSON defaults to task completed"""
        mock_llm = MockLLM(responses={"请判断": "This is not valid JSON"})
        plugin = ReflectLLM(llm=mock_llm)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test",
            params={},
            layer="reflect",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"result": {"data": "value"}},
        )

        result = plugin.execute(context)

        # Conservative: default to completed on error
        assert result.success is True
        assert result.data["task_completed"] is True
        assert "解析失败" in result.data["reason"]

    def test_llm_call_raises_exception_defaults_to_completed(self):
        """Test that LLM exception defaults to task completed"""

        class FailingLLM:
            def complete(self, messages, temperature=0.7, max_tokens=None):
                raise RuntimeError("LLM service unavailable")

        plugin = ReflectLLM(llm=FailingLLM())

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test",
            params={},
            layer="reflect",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"result": {"data": "value"}},
        )

        result = plugin.execute(context)

        # Conservative: default to completed on error
        assert result.success is True
        assert result.data["task_completed"] is True
        assert "LLM调用失败" in result.data["reason"]

    def test_custom_min_quality_score(self):
        """Test custom minimum quality score threshold"""
        reflect_response = json.dumps(
            {"completed": True, "reason": "结果可用", "quality_score": 75}
        )

        mock_llm = MockLLM(responses={"请判断": reflect_response})
        plugin = ReflectLLM(llm=mock_llm, min_quality_score=80)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test",
            tool_description="Test",
            params={},
            layer="reflect",
            execution_id="test-123",
            timestamp=time.time(),
            previous_results={"result": {"data": "value"}},
        )

        result = plugin.execute(context)

        # Quality 75 < threshold 80
        assert result.success is True
        assert result.data["task_completed"] is False
        assert result.data["quality_score"] == 75
