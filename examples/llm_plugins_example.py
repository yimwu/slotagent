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

    # ------------------------------------------------------------
    # Test 1: Normal execution with Reflect
    # ------------------------------------------------------------
    print("=" * 60)
    print("Test 1: Normal execution (should trigger Reflect)")
    print("=" * 60)

    context = scheduler.execute("weather_query", {"location": "Beijing"})

    print(f"Status: {context.status}")
    print(f"Result: {context.final_result}")

    if "reflect" in context.plugin_results:
        reflect_result = context.plugin_results["reflect"]
        print("\nReflect Analysis:")
        print(f"  Task Completed: {reflect_result.data.get('task_completed')}")
        print(f"  Quality Score: {reflect_result.data.get('quality_score')}")
        print(f"  Reason: {reflect_result.data.get('reason')}")

    # ------------------------------------------------------------
    # Test 2: Tool failure with Healing
    # ------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Test 2: Tool failure (should trigger Healing retry)")
    print("=" * 60)

    # Create a tool that fails first time, succeeds second time
    call_count = {"count": 0}

    def unreliable_weather(params):
        call_count["count"] += 1
        location = params.get("location", "")
        # First call fails with bad location
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

    print(f"Calling with bad location 'Beiing' (misspelled)...")
    context = scheduler.execute("unreliable_weather", {"location": "Beiing"})

    print(f"Status: {context.status}")
    print(f"Call count: {call_count['count']}")
    print(f"Final result: {context.final_result}")

    if "healing" in context.plugin_results:
        healing_result = context.plugin_results["healing"]
        print("\nHealing Analysis:")
        print(f"  Recovered: {healing_result.data.get('recovered')}")
        print(f"  Analysis: {healing_result.data.get('analysis')}")
        print(f"  Fixed params: {healing_result.data.get('fixed_params')}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
