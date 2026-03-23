#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Independent Mode Example - Natural Language Tool Interaction with Real LLM

Demonstrates how to use SlotAgent in independent mode with a real LLM
(Qwen/通义千问). The agent processes natural-language queries,
automatically selects the appropriate tool via LLM, and executes it
through the full plugin chain (Schema -> Guard -> Execute -> Healing -> Reflect).

================================================================================
PREREQUISITES
================================================================================

1. Set the DASHSCOPE_PLAN_API_KEY environment variable:
   Windows CMD:
     set DASHSCOPE_PLAN_API_KEY=your-api-key-here
   Windows PowerShell:
     $env:DASHSCOPE_PLAN_API_KEY="your-api-key-here"
   Linux/Mac:
     export DASHSCOPE_PLAN_API_KEY=your-api-key-here

2. Or modify the QWEN_CONFIG dict below with your credentials.

3. Install dependencies:
     pip install -e .

================================================================================
LLM API CONFIGURATION
================================================================================

This example uses 阿里云百炼 (Alibaba Cloud Bailian) Qwen series models.
Other compatible LLM providers can be used by implementing the LLMInterface:

  from slotagent.llm.interface import LLMInterface, LLMMessage

  class YourLLM(LLMInterface):
      def complete(self, messages, temperature=0.7, max_tokens=None):
          # Implement your LLM call here
          pass

Supported model endpoints (OpenAI-compatible):
  - 阿里云百炼: https://coding.dashscope.aliyuncs.com/v1
  - OpenAI: https://api.openai.com/v1
  - Anthropic: https://api.anthropic.com/v1 (requires custom client)
  - Azure OpenAI: https://YOUR_RESOURCE.openai.azure.com/v1

For other providers, check their API documentation for:
  - Endpoint URL (base_url)
  - Model name (model)
  - Authentication method (API key / Bearer token)
  - Request/response format

================================================================================
"""

import os
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from slotagent import SlotAgent
from slotagent.llm import QwenLLM
from slotagent.plugins import HealingLLM, ReflectLLM, SchemaDefault, GuardDefault
from slotagent.types import ExecutionStatus, Tool


# =============================================================================
# LLM CONFIGURATION
# =============================================================================
# IMPORTANT: Modify these values to match your LLM provider configuration.
#
# For 阿里云百炼 (Alibaba Cloud Bailian):
#   - base_url: https://coding.dashscope.aliyuncs.com/v1
#   - model: qwen3.5-plus (or other available models)
#   - api_key: Get from https://bailian.console.aliyun.com/
#
# For OpenAI:
#   - base_url: https://api.openai.com/v1
#   - model: gpt-4o
#   - api_key: Get from https://platform.openai.com/api-keys
#
# For other providers, refer to their API documentation.
# =============================================================================

QWEN_CONFIG = {
    # API endpoint - DO NOT include /chat/completions suffix
    "base_url": "https://coding.dashscope.aliyuncs.com/v1",
    # Model name - check your provider's available models
    "model": "qwen3.5-plus",
    # API key - read from environment variable for security
    # Or set directly: "api_key": "your-key-here"
    "api_key_env": "DASHSCOPE_PLAN_API_KEY",
}


def create_llm():
    """
    Create LLM instance from configuration.

    Modify QWEN_CONFIG above to use a different LLM provider.
    """
    api_key = os.getenv(QWEN_CONFIG["api_key_env"])
    if not api_key:
        raise EnvironmentError(
            f"API key not found. Please set the {QWEN_CONFIG['api_key_env']} "
            f"environment variable:\n"
            f"  Windows: set {QWEN_CONFIG['api_key_env']}=your-key\n"
            f"  Linux/Mac: export {QWEN_CONFIG['api_key_env']}=your-key"
        )

    # Note: If using a different LLM provider, replace QwenLLM with your
    # implementation. Example for OpenAI:
    #
    #   from openai import OpenAI
    #   class OpenAILLM(LLMInterface):
    #       def __init__(self, api_key, model="gpt-4o"):
    #           self.client = OpenAI(api_key=api_key)
    #           self.model = model
    #       def complete(self, messages, temperature=0.7, max_tokens=None):
    #           resp = self.client.chat.completions.create(
    #               model=self.model,
    #               messages=[{"role": m.role, "content": m.content} for m in messages],
    #               temperature=temperature,
    #               max_tokens=max_tokens,
    #           )
    #           return LLMResponse(
    #               content=resp.choices[0].message.content,
    #               model=self.model,
    #           )

    return QwenLLM(
        api_key=api_key,
        base_url=QWEN_CONFIG["base_url"],
        model=QWEN_CONFIG["model"],
    )


# =============================================================================
# Tool Definitions
# =============================================================================
# These tools are registered with the agent. The LLM will automatically
# select the appropriate tool based on the user's natural-language query.
# =============================================================================


def get_weather(params):
    """Fetch current weather for a location."""
    location = params.get("location", "Unknown")
    return {
        "location": location,
        "temperature": 25,
        "condition": "sunny",
        "humidity": 60,
    }


def search_news(params):
    """Search for news articles by keyword."""
    keyword = params.get("keyword", "")
    return {
        "keyword": keyword,
        "articles": [
            {"title": f"News about {keyword}", "source": "NewsSite", "date": "2026-03-24"},
            {"title": f"Latest update on {keyword}", "source": "Media", "date": "2026-03-23"},
        ],
        "count": 2,
    }


def calculate(params):
    """Perform arithmetic calculation on two numbers."""
    a = params.get("a", 0)
    b = params.get("b", 0)
    operation = params.get("operation", "add")

    operations = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else "undefined",
    }

    result = operations.get(operation, "unknown operation")
    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result,
    }


# =============================================================================
# Main Example
# =============================================================================


def main():
    print("=" * 70)
    print("  SlotAgent Independent Mode - Natural Language Tool Interaction")
    print("=" * 70)
    print()

    # -----------------------------------------------------------------
    # Step 1: Create LLM instance
    # -----------------------------------------------------------------
    print("[1] Initializing LLM...")
    try:
        llm = create_llm()
        print(f"    Model: {llm.model}")
        print(f"    Endpoint: {llm.base_url}")
    except EnvironmentError as e:
        print(f"    ERROR: {e}")
        return
    print()

    # -----------------------------------------------------------------
    # Step 2: Create SlotAgent in independent mode
    # -----------------------------------------------------------------
    print("[2] Creating SlotAgent in independent mode...")
    agent = SlotAgent(llm=llm)
    print("    Agent created with LLM: enabled")
    print()

    # -----------------------------------------------------------------
    # Step 3: Register global plugins
    # -----------------------------------------------------------------
    print("[3] Registering plugins...")
    # Healing: Auto-retry on failure with LLM-driven parameter fixing
    agent.register_plugin(HealingLLM(llm=llm, temperature=0.3))
    # Reflect: Verify task completion with LLM-driven quality check
    agent.register_plugin(ReflectLLM(llm=llm, temperature=0.2, min_quality_score=60))
    print("    - HealingLLM: Auto-recovery on tool failure")
    print("    - ReflectLLM: Task completion verification")
    print()

    # -----------------------------------------------------------------
    # Step 4: Register tools
    # -----------------------------------------------------------------
    print("[4] Registering tools...")

    weather_tool = Tool(
        tool_id="weather_query",
        name="Weather Query",
        description="Get current weather information for a specified city or location",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City or location name"},
            },
            "required": ["location"],
        },
        execute_func=get_weather,
    )

    news_tool = Tool(
        tool_id="news_search",
        name="News Search",
        description="Search for recent news articles by keyword",
        input_schema={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Search keyword"},
            },
            "required": ["keyword"],
        },
        execute_func=search_news,
    )

    calc_tool = Tool(
        tool_id="calculator",
        name="Calculator",
        description="Perform basic arithmetic operations on two numbers",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"},
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "Arithmetic operation",
                },
            },
            "required": ["a", "b", "operation"],
        },
        execute_func=calculate,
    )

    agent.register_tool(weather_tool)
    agent.register_tool(news_tool)
    agent.register_tool(calc_tool)
    print(f"    - {weather_tool.name} ({weather_tool.tool_id})")
    print(f"    - {news_tool.name} ({news_tool.tool_id})")
    print(f"    - {calc_tool.name} ({calc_tool.tool_id})")
    print()

    # -----------------------------------------------------------------
    # Step 5: Execute natural-language queries
    # -----------------------------------------------------------------
    print("=" * 70)
    print("  Executing Natural Language Queries")
    print("=" * 70)
    print()

    queries = [
        # Query 1: Weather tool
        "What's the weather in Beijing?",
        # Query 2: Calculator tool
        "Calculate 15 plus 27",
        # Query 3: News search
        "Search for news about AI",
    ]

    for i, query in enumerate(queries, 1):
        print(f"Query {i}: \"{query}\"")
        print("-" * 60)

        # The agent uses LLM to:
        # 1. Understand the query
        # 2. Select the appropriate tool
        # 3. Extract parameters from natural language
        # 4. Execute through the plugin chain
        # 5. Return the result
        ctx = agent.run(query)

        print(f"    Selected tool: {ctx.tool_id}")
        print(f"    Status: {ctx.status}")

        if ctx.status == ExecutionStatus.COMPLETED:
            print(f"    Result: {ctx.final_result}")

            # Show Reflect analysis if available
            if "reflect" in ctx.plugin_results:
                reflect = ctx.plugin_results["reflect"]
                if reflect.data:
                    print(
                        f"    Reflect: completed={reflect.data.get('task_completed')}, "
                        f"quality={reflect.data.get('quality_score')}"
                    )
        elif ctx.status == ExecutionStatus.FAILED:
            print(f"    Error: {ctx.error}")

            # Show Healing analysis if available (tool failed but was retried)
            if "healing" in ctx.plugin_results:
                healing = ctx.plugin_results["healing"]
                if healing.data and healing.data.get("recovered"):
                    print(
                        f"    Healing: recovered=True, "
                        f"fixed_params={healing.data.get('fixed_params')}"
                    )
        else:
            print(f"    Pending approval: {ctx.approval_id}")

        print()

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------
    print("=" * 70)
    print("  Summary")
    print("=" * 70)
    print()
    print("In independent mode, the LLM handles:")
    print("  1. Tool Selection - choosing the right tool for the query")
    print("  2. Parameter Extraction - converting natural language to params")
    print()
    print("The full plugin chain executes on each tool call:")
    print("  Schema -> Guard -> Execute -> Healing (if failed) -> Reflect")
    print()
    print("Done!")


if __name__ == "__main__":
    main()
