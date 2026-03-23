# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Integration tests for LLM plugins (HealingLLM + ReflectLLM).

Tests the complete plugin chain with LLM integration.
"""

import json
import time

import pytest

from slotagent.core import CoreScheduler
from slotagent.llm import MockLLM
from slotagent.plugins.healing import HealingLLM
from slotagent.plugins.reflect import ReflectLLM
from slotagent.plugins.schema import SchemaDefault
from slotagent.types import ExecutionStatus, Tool


class TestHealingIntegration:
    """Integration tests for Healing workflow"""

    def test_healing_fixes_parameter_and_retries(self):
        """Test healing plugin fixes parameters and retries successfully"""

        # Setup mock LLM with healing response
        mock_llm = MockLLM(
            responses={
                "执行错误": json.dumps({
                    "analysis": "参数location拼写错误，应该是Beijing而不是Beiing",
                    "fixed_params": {"location": "Beijing"}
                })
            }
        )

        # Setup scheduler with healing plugin
        scheduler = CoreScheduler(llm=mock_llm)
        healing_plugin = HealingLLM(llm=mock_llm, max_retries=1)
        scheduler.plugin_pool.register_global_plugin(healing_plugin)

        # Create tool that fails on first call but succeeds on retry
        call_count = {"n": 0}

        def failing_weather_tool(params):
            call_count["n"] += 1
            location = params.get("location", "")

            # First call fails with typo
            if call_count["n"] == 1 and location == "Beiing":
                raise RuntimeError("City not found: Beiing")

            # Second call succeeds with corrected location
            if call_count["n"] == 2 and location == "Beijing":
                return {"temperature": 25, "city": "Beijing", "condition": "sunny"}

            raise RuntimeError(f"Unexpected call: {params}")

        tool = Tool(
            tool_id="weather_query",
            name="天气查询",
            description="获取指定城市的天气信息",
            input_schema={
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            },
            execute_func=failing_weather_tool,
        )

        scheduler.register_tool(tool)

        # Execute with bad parameter
        context = scheduler.execute("weather_query", {"location": "Beiing"})

        # Should succeed after healing
        assert context.status == ExecutionStatus.COMPLETED
        assert call_count["n"] == 2  # Original call + retry
        assert len(mock_llm.call_history) >= 1  # LLM called for healing
        assert "healing" in context.plugin_results

        # Verify healing worked
        healing_result = context.plugin_results["healing"]
        assert healing_result.data.get("recovered") is True
        assert healing_result.data.get("fixed_params") == {"location": "Beijing"}

        # Final result should be success
        assert context.final_result["temperature"] == 25
        assert context.final_result["city"] == "Beijing"

    def test_healing_fails_when_llm_cannot_fix(self):
        """Test healing fails gracefully when LLM cannot fix parameters"""

        # LLM responds that it cannot fix the error
        mock_llm = MockLLM(
            responses={
                "error": json.dumps({
                    "analysis": "无法修复此错误",
                    "fixed_params": None
                })
            }
        )

        scheduler = CoreScheduler(llm=mock_llm)
        healing_plugin = HealingLLM(llm=mock_llm, max_retries=1)
        scheduler.plugin_pool.register_global_plugin(healing_plugin)

        def always_failing_tool(params):
            raise RuntimeError("Permanent failure")

        tool = Tool(
            tool_id="failing_tool",
            name="Failing Tool",
            description="A tool that always fails",
            input_schema={"type": "object", "properties": {}},
            execute_func=always_failing_tool,
        )

        scheduler.register_tool(tool)
        context = scheduler.execute("failing_tool", {})

        # Should fail after healing attempt
        assert context.status == ExecutionStatus.FAILED
        assert "healing" in context.plugin_results

        healing_result = context.plugin_results["healing"]
        assert healing_result.data.get("recovered") is False


class TestHealingReflectIntegration:
    """Integration tests for Healing + Reflect workflow"""

    def test_reflect_validates_successful_execution(self):
        """Test reflect plugin validates successful tool execution"""

        mock_llm = MockLLM(
            responses={
                # Reflect response: validate the result
                "请判断": json.dumps(
                    {
                        "completed": True,
                        "reason": "结果包含温度和天气状况",
                        "quality_score": 95,
                    }
                ),
            }
        )

        scheduler = CoreScheduler(llm=mock_llm)
        scheduler.plugin_pool.register_global_plugin(ReflectLLM(llm=mock_llm))

        def weather_func(params):
            return {"location": params["location"], "temperature": 20, "condition": "sunny"}

        weather_tool = Tool(
            tool_id="weather_query",
            name="天气查询",
            description="获取指定城市的天气信息",
            input_schema={
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
            execute_func=weather_func,
        )

        scheduler.register_tool(weather_tool)
        context = scheduler.execute("weather_query", {"location": "Beijing"})

        # Tool succeeded
        assert context.status == ExecutionStatus.COMPLETED

        # Reflect was called
        assert len(mock_llm.call_history) >= 1
        assert "reflect" in context.plugin_results

        # Reflect validated the result
        reflect_result = context.plugin_results["reflect"]
        assert reflect_result.data["task_completed"] is True
        assert reflect_result.data["quality_score"] == 95

    def test_reflect_marks_low_quality_result(self):
        """Test reflect plugin marks low quality results"""

        mock_llm = MockLLM(
            responses={
                "请判断": json.dumps(
                    {
                        "completed": False,
                        "reason": "结果缺少必要字段",
                        "quality_score": 40,
                    }
                )
            }
        )

        scheduler = CoreScheduler(llm=mock_llm)
        scheduler.plugin_pool.register_global_plugin(ReflectLLM(llm=mock_llm))

        def incomplete_tool(params):
            return {"incomplete": "data"}  # Low quality result

        tool = Tool(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=incomplete_tool,
        )

        scheduler.register_tool(tool)
        context = scheduler.execute("test_tool", {})

        # Tool executed successfully
        assert context.status == ExecutionStatus.COMPLETED

        # But reflect marked it as low quality
        reflect_result = context.plugin_results.get("reflect")
        assert reflect_result is not None

        # Check the actual data structure returned
        assert "task_completed" in reflect_result.data
        assert reflect_result.data["task_completed"] is False

        # Quality score should be in the data
        if "quality_score" in reflect_result.data:
            assert reflect_result.data["quality_score"] == 40

    def test_without_llm_plugins_tool_executes_normally(self):
        """Test that tools work normally without LLM plugins"""

        scheduler = CoreScheduler()  # No LLM

        def simple_tool(params):
            return {"result": "success"}

        tool = Tool(
            tool_id="simple_tool",
            name="Simple Tool",
            description="A simple tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=simple_tool,
        )

        scheduler.register_tool(tool)
        context = scheduler.execute("simple_tool", {})

        assert context.status == ExecutionStatus.COMPLETED
        assert context.final_result == {"result": "success"}

        # No healing or reflect plugins executed
        assert "healing" not in context.plugin_results
        assert "reflect" not in context.plugin_results


class TestToolLevelPluginConfiguration:
    """Test tool-level plugin configuration with LLM plugins"""

    def test_tool_specific_llm_plugins(self):
        """Test different tools using different LLM plugin configurations"""

        mock_llm = MockLLM(
            responses={
                "请判断": json.dumps(
                    {"completed": True, "reason": "ok", "quality_score": 90}
                )
            }
        )

        scheduler = CoreScheduler(llm=mock_llm)

        # Register reflect plugin globally
        reflect_plugin = ReflectLLM(llm=mock_llm)
        scheduler.plugin_pool.register_global_plugin(reflect_plugin)

        # Tool 1: Uses global reflect
        def tool1_func(params):
            return {"data": "value1"}

        tool1 = Tool(
            tool_id="tool1",
            name="Tool 1",
            description="First tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=tool1_func,
            # No plugins specified - uses global
        )

        # Tool 2: Explicitly disables plugins (no reflect configured for it)
        def tool2_func(params):
            return {"data": "value2"}

        tool2 = Tool(
            tool_id="tool2",
            name="Tool 2",
            description="Second tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=tool2_func,
            plugins={},  # Empty - no tool-specific plugins
        )

        scheduler.register_tool(tool1)
        scheduler.register_tool(tool2)

        # Execute tool1 - should use reflect
        context1 = scheduler.execute("tool1", {})
        assert "reflect" in context1.plugin_results

        # Execute tool2 - should also use global reflect
        # (tool-level plugins override but empty dict doesn't remove global)
        context2 = scheduler.execute("tool2", {})
        assert "reflect" in context2.plugin_results
