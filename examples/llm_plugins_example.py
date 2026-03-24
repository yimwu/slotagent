#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
LLM Plugins Example - Healing and Reflect with LLM

Demonstrates how to use LLM-powered Healing and Reflect plugins
with real Qwen (通义千问) LLM.
"""

import json
import os
import sys

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from slotagent.core import CoreScheduler
from slotagent.llm import QwenLLM
from slotagent.plugins import HealingLLM, ReflectLLM
from slotagent.types import Tool


def main():
    print("=== LLM Plugins Example (Real Qwen LLM) ===\n")

    # Check API key
    api_key = os.getenv("DASHSCOPE_PLAN_API_KEY")
    if not api_key:
        print("ERROR: DASHSCOPE_PLAN_API_KEY environment variable not set")
        print("Please set it before running this example:")
        print("  Windows: set DASHSCOPE_PLAN_API_KEY=your-key")
        print("  Linux/Mac: export DASHSCOPE_PLAN_API_KEY=your-key")
        return

    # Create real Qwen LLM
    # Base URL: https://coding.dashscope.aliyuncs.com/v1
    # Model: qwen3.5-plus
    qwen_llm = QwenLLM(
        api_key=api_key,
        model="qwen3.5-plus"
    )

    print(f"Using model: {qwen_llm.model}")
    print(f"API base: {qwen_llm.base_url}\n")

    # Create scheduler with LLM
    scheduler = CoreScheduler(llm=qwen_llm)

    # Register LLM plugins
    healing_plugin = HealingLLM(llm=qwen_llm, temperature=0.3)
    reflect_plugin = ReflectLLM(llm=qwen_llm, temperature=0.2, min_quality_score=70)

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
        name="Weather Query",
        description="Get current weather information for a specified location",
        input_schema={
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
        execute_func=get_weather,
    )

    scheduler.register_tool(weather_tool)

    # =================================================================
    # Test 1: Normal execution with Reflect
    # =================================================================
    # 【执行流程】
    #   Step 1. Schema 层    → 验证 {"location": "Beijing"} 通过
    #   Step 2. Guard 层     → 通过（无需人工审批，工具不在黑名单）
    #   Step 3. Execute 层   → 调用 get_weather，正常返回天气数据
    #   Step 4. Healing 层   → 【不触发】工具执行成功，无需自愈
    #   Step 5. Reflect 层   → 分析结果，评估质量分数
    #   Step 6. Observe 层   → 记录日志
    #
    # 【plugin_results 包含】: schema, guard, execute, reflect, observe
    # 【注意】: 没有 "healing" 键，因为工具执行成功
    # =================================================================
    print("=" * 60)
    print("Test 1: Normal execution (should trigger Reflect)")
    print("=" * 60)

    context = scheduler.execute("weather_query", {"location": "Beijing"})

    print(f"Status: {context.status}")
    print(f"Result: {context.final_result}")

    if "healing" in context.plugin_results:
        # 这个分支不会执行，因为工具执行成功了
        healing_result = context.plugin_results["healing"]
        print("\nHealing Analysis:")
        print(f"  Recovered: {healing_result.data.get('recovered')}")
        print(f"  Analysis: {healing_result.data.get('analysis')}")
        print(f"  Fixed params: {healing_result.data.get('fixed_params')}")

    if "reflect" in context.plugin_results:
        # 这个分支会执行，因为工具执行成功了
        reflect_result = context.plugin_results["reflect"]
        print("\nReflect Analysis:")
        print(f"  Task Completed: {reflect_result.data.get('task_completed')}")
        print(f"  Quality Score: {reflect_result.data.get('quality_score')}")
        print(f"  Reason: {reflect_result.data.get('reason')}")

    # =================================================================
    # Test 2: Tool failure with Healing
    # =================================================================
    # 【工具行为】
    #   unreliable_weather 只在"第一次调用 且 location 不是 Beijing"时失败
    #   第二次调用会成功（无论 location 是什么）
    #
    # 【执行流程】
    #   Step 1. Schema 层    → 验证 {"location": "Beiing"} 通过
    #   Step 2. Guard 层     → 通过
    #   Step 3. Execute 层   → 调用工具，抛出 ValueError("Invalid location: Beiing")
    #                         call_count = 1，第一次失败
    #   Step 4. Healing 层   → 【触发！】分析错误原因，修正参数
    #                         - 分析: "Beiing 是 Beijing 的拼写错误"
    #                         - 修复: {"location": "Beijing"}
    #   Step 5. Execute 层   → 重试，call_count = 2
    #                         - location = "Beijing"，这次成功
    #   Step 6. Reflect 层   → 分析重试后的结果
    #   Step 7. Observe 层   → 记录日志
    #
    # 【plugin_results 包含】: schema, guard, execute, healing, execute(retry), reflect, observe
    # 【注意】: 有 "healing" 键，因为工具第一次执行失败了
    # =================================================================
    print("\n" + "=" * 60)
    print("Test 2: Tool failure (should trigger Healing retry)")
    print("=" * 60)

    # 计数器：记录工具被调用了多少次
    call_count = {"count": 0}

    def unreliable_weather(params):
        call_count["count"] += 1
        location = params.get("location", "")
        # 第一次调用且非 "Beijing" 时抛出错误
        if call_count["count"] == 1 and location != "Beijing":
            raise ValueError(f"Invalid location: {location}")
        return {
            "location": params.get("location", "Unknown"),
            "temperature": 22,
            "condition": "cloudy",
            "humidity": 55,
        }

    unreliable_tool = Tool(
        tool_id="unreliable_weather",
        name="Unreliable Weather",
        description="Weather query that may fail initially but recovers",
        input_schema={
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
        execute_func=unreliable_weather,
    )

    scheduler.register_tool(unreliable_tool)

    # 传入拼写错误的 "Beiing"（不是 "Beijing"），触发第一次失败
    # LLM 会分析错误原因，修正参数后重试
    print(f"Calling with bad location 'Beiing' (misspelled)...")
    context = scheduler.execute("unreliable_weather", {"location": "Beiing"})

    print(f"Status: {context.status}")
    print(f"Call count: {call_count['count']}")  # 期望: 2（失败1次 + 重试1次）
    print(f"Final result: {context.final_result}")

    # 检查 Healing 是否被触发（工具失败时会有这个键）
    if "healing" in context.plugin_results:
        healing_result = context.plugin_results["healing"]
        print("\nHealing Analysis:")
        print(f"  Recovered: {healing_result.data.get('recovered')}")  # 期望: True
        print(f"  Analysis: {healing_result.data.get('analysis')}")   # 期望: "Beiing 是拼写错误"
        print(f"  Fixed params: {healing_result.data.get('fixed_params')}")  # 期望: {"location": "Beijing"}

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
