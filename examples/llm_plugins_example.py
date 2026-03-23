# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
LLM Plugins Example - Healing and Reflect with LLM

Demonstrates how to use LLM-powered Healing and Reflect plugins.
"""

import json

from slotagent.core import CoreScheduler
from slotagent.llm import MockLLM
from slotagent.plugins import HealingLLM, ReflectLLM
from slotagent.types import Tool


def main():
    print("=== LLM Plugins Example ===\n")

    # Create Mock LLM with preset responses
    # In production, use QwenLLM or other real LLM
    mock_llm = MockLLM(
        responses={
            "执行错误": json.dumps(
                {
                    "analysis": "城市名拼写错误,应该是Beijing而不是Beiing",
                    "fixed_params": {"location": "Beijing"},
                }
            ),
            "请判断": json.dumps(
                {
                    "completed": True,
                    "reason": "结果包含温度和天气状况,符合工具目标",
                    "quality_score": 95,
                }
            ),
        }
    )

    # Create scheduler with LLM
    scheduler = CoreScheduler(llm=mock_llm)

    # Register LLM plugins
    healing_plugin = HealingLLM(llm=mock_llm, temperature=0.3)
    reflect_plugin = ReflectLLM(llm=mock_llm, temperature=0.2, min_quality_score=70)

    scheduler.plugin_pool.register_global_plugin(healing_plugin)
    scheduler.plugin_pool.register_global_plugin(reflect_plugin)

    # Define a simple weather tool
    def get_weather(params):
        location = params.get("location")
        return {
            "location": location,
            "temperature": 20,
            "condition": "sunny",
            "humidity": 60,
        }

    weather_tool = Tool(
        tool_id="weather_query",
        name="天气查询",
        description="获取指定城市的天气信息",
        input_schema={
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
        execute_func=get_weather,
    )

    scheduler.register_tool(weather_tool)

    # Execute tool
    print("Executing weather query for Beijing...")
    context = scheduler.execute("weather_query", {"location": "Beijing"})

    print(f"Status: {context.status}")
    print(f"Result: {context.final_result}")

    # Check Reflect result
    if "reflect" in context.plugin_results:
        reflect_result = context.plugin_results["reflect"]
        print("\nReflect Analysis:")
        print(f"  Task Completed: {reflect_result.data.get('task_completed')}")
        print(f"  Quality Score: {reflect_result.data.get('quality_score')}")
        print(f"  Reason: {reflect_result.data.get('reason')}")

    print("\nLLM Call History:")
    for i, call in enumerate(mock_llm.call_history, 1):
        print(f"  Call {i}: {call[-1].content[:80]}...")


if __name__ == "__main__":
    main()
