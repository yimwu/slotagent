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
PLUGIN CHAIN DEMONSTRATION
================================================================================

This example demonstrates the complete 6-layer plugin chain by switching
between independent mode (LLM picks and executes tools) and embedded mode
(direct tool execution with full plugin control).

Layer   | Independent Mode                    | Embedded Mode
--------|-------------------------------------|----------------------------------
Schema  | LLM-generated params validated      | SchemaDefault validates params
Guard   | Access control enforced            | GuardDefault blocks/approves
Execute | Tool runs with LLM-provided params | Tool runs with explicit params
Healing | Triggers on tool failure           | Triggers on tool failure (demo)
Reflect | LLM verifies task completion       | LLM verifies task completion

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
from slotagent.core import HookManager
from slotagent.llm import QwenLLM
from slotagent.plugins import (
    HealingLLM,
    ReflectLLM,
    SchemaDefault,
    GuardDefault,
)
from slotagent.types import ExecutionStatus, PluginResult, Tool


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
    "api_key_env": "DASHSCOPE_PLAN_API_KEY",
}


def create_llm():
    """Create LLM instance from configuration. Modify QWEN_CONFIG above."""
    api_key = os.getenv(QWEN_CONFIG["api_key_env"])
    if not api_key:
        raise EnvironmentError(
            f"API key not found. Please set {QWEN_CONFIG['api_key_env']} "
            f"environment variable:\n"
            f"  Windows: set {QWEN_CONFIG['api_key_env']}=your-key\n"
            f"  Linux/Mac: export {QWEN_CONFIG['api_key_env']}=your-key"
        )
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
# Hook Monitor - tracks plugin chain execution for demo display
# =============================================================================

def create_hook_monitor():
    """Create a HookManager that records all events for demo display."""
    hook_manager = HookManager()

    def on_before(event):
        print(f"    [Hook] before_exec: {event.tool_id} with params={event.params}")

    def on_after(event):
        print(
            f"    [Hook] after_exec: {event.tool_id}, "
            f"time={event.execution_time:.3f}s"
        )

    def on_fail(event):
        print(
            f"    [Hook] fail: {event.tool_id}, "
            f"error={event.error}, stage={event.failed_stage}"
        )

    def on_guard_block(event):
        print(f"    [Hook] guard_block: {event.tool_id}, reason={event.reason}")

    def on_wait_approval(event):
        print(
            f"    [Hook] wait_approval: {event.tool_id}, "
            f"approval_id={event.approval_id}"
        )

    hook_manager.subscribe("before_exec", on_before)
    hook_manager.subscribe("after_exec", on_after)
    hook_manager.subscribe("fail", on_fail)
    hook_manager.subscribe("guard_block", on_guard_block)
    hook_manager.subscribe("wait_approval", on_wait_approval)

    return hook_manager


# =============================================================================
# Demo Sections
# =============================================================================


def demo_independent_mode(agent, llm, hook_mgr):
    """
    Demonstrate INDEPENDENT MODE: LLM picks tool and params from natural language.

    Plugin chain layers triggered:
      Schema -> Guard -> Execute -> Reflect

    Note: Healing is NOT triggered here (no tool failure occurs).
    """
    print("\n" + "=" * 70)
    print("  PART 1: Independent Mode (LLM Picks Tools)")
    print("=" * 70)
    print()
    print("  The agent receives a natural-language query and uses LLM to:")
    print("    1. Select the appropriate tool")
    print("    2. Extract parameters from natural language")
    print("    3. Execute through the plugin chain")
    print()
    print("  Plugin layers activated: Schema -> Guard -> Execute -> Reflect")
    print()

    queries = [
        ("What's the weather in Beijing?", "weather_query"),
        ("Calculate 15 plus 27", "calculator"),
        ("Search for news about AI", "news_search"),
    ]

    for i, (query, expected_tool) in enumerate(queries, 1):
        print(f"  Query {i}: \"{query}\"")
        print("-" * 66)

        ctx = agent.run(query)

        print(f"    Tool selected: {ctx.tool_id} (expected: {expected_tool})")
        print(f"    Status: {ctx.status}")

        if ctx.status == ExecutionStatus.COMPLETED:
            print(f"    Result: {ctx.final_result}")
            if "reflect" in ctx.plugin_results:
                r = ctx.plugin_results["reflect"]
                if r.data:
                    print(
                        f"    Reflect: quality={r.data.get('quality_score')}, "
                        f"completed={r.data.get('task_completed')}"
                    )
        print()


def demo_plugin_layers_embedded(agent, llm, hook_mgr):
    """
    Demonstrate each plugin layer with EMBEDDED MODE (explicit execute()).

    This section uses direct execute() calls to precisely control which
    plugin layers are triggered, demonstrating the full 6-layer chain.

    Layer 1 - Schema:   Reject invalid params before execution
    Layer 2 - Guard:    Block/blacklist/whitelist access control
    Layer 3 - Execute:  Tool runs with provided params
    Layer 4 - Healing:  Tool fails -> LLM fixes -> retry succeeds
    Layer 5 - Reflect:  LLM verifies task completion
    Layer 6 - Observe: LogPlugin records lifecycle events
    """
    print("\n" + "=" * 70)
    print("  PART 2: Plugin Chain Layers (Embedded Mode)")
    print("=" * 70)
    print()
    print("  Using execute() for precise control over plugin layers.")
    print("  Each demo shows exactly which layer is being tested.")
    print()

    # -----------------------------------------------------------------
    # Layer 1: Schema validation
    # -----------------------------------------------------------------
    print("  [Layer 1: Schema] Invalid params rejected before execution")
    print("-" * 66)
    # Missing required 'location' param
    ctx = agent.execute("weather_query", {})  # no location
    print(f"    Params sent: {{}}  (missing required 'location')")
    print(f"    Status: {ctx.status}")
    print(f"    Error: {ctx.error}")
    print(f"    Tool was NOT executed (blocked at Schema layer)")
    print()

    # -----------------------------------------------------------------
    # Layer 2: Guard - whitelist blocking
    # -----------------------------------------------------------------
    print("  [Layer 2: Guard] Access control blocks tool")
    print("-" * 66)
    # send_money has a whitelist that only allows "admin" role
    ctx = agent.execute("send_money", {"amount": 100, "to": "user123"})
    print(f"    Params sent: amount=100, to=user123")
    print(f"    Status: {ctx.status}")
    print(f"    Error: {ctx.error}")
    print(f"    Tool was NOT executed (blocked at Guard layer)")
    print()

    # -----------------------------------------------------------------
    # Layer 3: Normal execution with Schema + Guard + Reflect
    # -----------------------------------------------------------------
    print("  [Layers 1+2+5: Schema + Guard + Reflect] Valid execution")
    print("-" * 66)
    ctx = agent.execute("weather_query", {"location": "Shanghai"})
    print(f"    Params sent: location=Shanghai")
    print(f"    Status: {ctx.status}")
    print(f"    Result: {ctx.final_result}")
    if "reflect" in ctx.plugin_results:
        r = ctx.plugin_results["reflect"]
        if r.data:
            print(
                f"    Reflect: quality={r.data.get('quality_score')}, "
                f"completed={r.data.get('task_completed')}"
            )
    print(f"    Plugin chain: Schema(pass) -> Guard(pass) -> Execute -> Reflect(verify)")
    print()

    # -----------------------------------------------------------------
    # Layer 4: Healing - tool fails, LLM fixes, retry succeeds
    # -----------------------------------------------------------------
    print("  [Layer 4: Healing] Tool failure -> LLM fixes params -> Retry")
    print("-" * 66)
    print(
        "    Tool 'location_checker' validates location names."
        "  When given a typo (e.g., 'Beiing'), it raises ValueError."
        "  HealingLLM uses LLM to analyze the error and fix the param."
    )
    ctx = agent.execute("location_checker", {"location": "Beiing"})  # typo
    print(f"    Params sent: location='Beiing' (misspelled)")
    print(f"    Status: {ctx.status}")
    print(f"    Tool was called once, failed, then retried with LLM-fixed params")

    if "healing" in ctx.plugin_results:
        h = ctx.plugin_results["healing"]
        if h.data:
            print(
                f"    Healing: recovered={h.data.get('recovered')}, "
                f"analysis={h.data.get('analysis')}, "
                f"fixed_params={h.data.get('fixed_params')}"
            )
    if ctx.final_result:
        print(f"    Final result: {ctx.final_result}")
    print(f"    Plugin chain: Execute(fail) -> Healing(LLM fix) -> Execute(retry)")
    print()

    # -----------------------------------------------------------------
    # Layer 2: Guard - additional blocking scenarios
    # -----------------------------------------------------------------
    print("  [Layer 2: Guard] Additional blocking scenarios")
    print("-" * 66)

    # delete_account is not whitelisted, so it's blocked
    ctx = agent.execute("delete_account", {"user_id": "user-123"})
    print(f"    Tool: delete_account, params: user_id=user-123")
    print(f"    Status: {ctx.status}")
    print(f"    Error: {ctx.error}")
    print(f"    Tool was NOT executed (blocked at Guard layer, not in whitelist)")
    print()


# =============================================================================
# Main
# =============================================================================


def main():
    print("=" * 70)
    print("  SlotAgent - Complete Plugin Chain Demo")
    print("  Independent Mode + Embedded Mode with Real LLM")
    print("=" * 70)
    print()

    # Create LLM
    print("[Init] Creating LLM instance...")
    try:
        llm = create_llm()
        print(f"    Model: {llm.model}")
        print(f"    Endpoint: {llm.base_url}")
    except EnvironmentError as e:
        print(f"    ERROR: {e}")
        return
    print()

    # Create hook monitor
    hook_mgr = create_hook_monitor()

    # Create SlotAgent in independent mode
    agent = SlotAgent(
        llm=llm,
        hook_manager=hook_mgr,
    )

    # Register global plugins
    agent.register_plugin(HealingLLM(llm=llm, temperature=0.3))
    agent.register_plugin(ReflectLLM(llm=llm, temperature=0.2, min_quality_score=60))

    # Register SchemaDefault globally (validates all tool params)
    agent.register_plugin(SchemaDefault())

    # Register GuardDefault with whitelist_only (blocks all non-whitelisted tools)
    agent.register_plugin(
        GuardDefault(
            whitelist=[
                "weather_query",
                "news_search",
                "calculator",
                "location_checker",  # Added so Healing can be triggered
            ],
            whitelist_only=True,
        )
    )

    print("[Init] Plugins registered:")
    print("    - SchemaDefault: validates all tool parameters")
    print("    - GuardDefault (whitelist_only): blocks non-whitelisted tools")
    print("    - HealingLLM: auto-recovery on tool failure")
    print("    - ReflectLLM: task completion verification")
    print()

    # Register tools
    # Tool 1: Weather (simple, no risk)
    agent.register_tool(Tool(
        tool_id="weather_query",
        name="Weather Query",
        description="Get current weather information for a specified city or location",
        input_schema={
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
        execute_func=get_weather,
    ))

    # Tool 2: News search (simple, no risk)
    agent.register_tool(Tool(
        tool_id="news_search",
        name="News Search",
        description="Search for recent news articles by keyword",
        input_schema={
            "type": "object",
            "properties": {"keyword": {"type": "string"}},
            "required": ["keyword"],
        },
        execute_func=search_news,
    ))

    # Tool 3: Calculator (simple, no risk)
    agent.register_tool(Tool(
        tool_id="calculator",
        name="Calculator",
        description="Perform basic arithmetic operations on two numbers",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                },
            },
            "required": ["a", "b", "operation"],
        },
        execute_func=calculate,
    ))

    # Tool 4: Money transfer (blocked by whitelist_only guard)
    def send_money_impl(params):
        return {
            "sent": True,
            "amount": params["amount"],
            "to": params["to"],
            "tx_id": "tx-1",
        }

    agent.register_tool(Tool(
        tool_id="send_money",
        name="Send Money",
        description="Transfer money to another user account",
        input_schema={
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "to": {"type": "string"},
            },
            "required": ["amount", "to"],
        },
        execute_func=send_money_impl,
    ))

    # Tool 5: Location checker (triggers Healing on typo)
    # This tool validates that the location name is spelled correctly.
    # On first call with "Beiing" (typo), it raises ValueError.
    # HealingLLM catches the error, asks LLM to fix params, retries.
    location_attempts = {"Beiing_seen": False}

    def location_checker_impl(params):
        location = params.get("location", "")
        # Simulate a tool that validates location names
        # Real tools (e.g., weather APIs) would reject invalid city names
        known_locations = {"Beijing", "Shanghai", "Guangzhou", "Shenzhen"}
        if location not in known_locations:
            # First attempt with invalid location -> fail
            if location == "Beiing" and not location_attempts["Beiing_seen"]:
                location_attempts["Beiing_seen"] = True
                raise ValueError(f"Unknown location: '{location}'. Did you mean Beijing?")
            # Second attempt after Healing fix -> succeed
            return {
                "location": location,
                "valid": True,
                "checked": True,
            }
        return {
            "location": location,
            "valid": True,
            "checked": True,
        }

    agent.register_tool(Tool(
        tool_id="location_checker",
        name="Location Checker",
        description="Verify if a city or location name is valid and known",
        input_schema={
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
        execute_func=location_checker_impl,
    ))

    # Tool 6: Delete account (blacklisted by GuardDefault)
    def delete_account_impl(params):
        return {"deleted": True, "user": params.get("user_id")}

    agent.register_tool(Tool(
        tool_id="delete_account",
        name="Delete Account",
        description="Permanently delete a user account (dangerous operation)",
        input_schema={
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
        execute_func=delete_account_impl,
    ))

    print("[Init] Tools registered:")
    print("    - weather_query: simple query (Schema + Guard + Execute + Reflect)")
    print("    - news_search: simple query")
    print("    - calculator: simple arithmetic")
    print("    - send_money: blocked by Guard (whitelist_only)")
    print("    - location_checker: whitelisted, triggers Healing on typo (Beiing -> Beijing)")
    print("    - delete_account: blocked by Guard (whitelist_only)")
    print()

    # -----------------------------------------------------------------
    # Part 1: Independent Mode
    # -----------------------------------------------------------------
    demo_independent_mode(agent, llm, hook_mgr)

    # -----------------------------------------------------------------
    # Part 2: Plugin Layers (Embedded Mode)
    # -----------------------------------------------------------------
    demo_plugin_layers_embedded(agent, llm, hook_mgr)

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------
    print("=" * 70)
    print("  Plugin Chain Summary")
    print("=" * 70)
    print()
    print("  Layer 1 - Schema:   Validates JSON Schema before execution")
    print("                      Demo: weather_query with missing location")
    print()
    print("  Layer 2 - Guard:    Access control (blacklist, whitelist)")
    print("                      Demo: delete_account (not in whitelist), send_money (not in whitelist)")
    print()
    print("  Layer 3 - Execute: Tool runs with provided parameters")
    print("                      Demo: all tools")
    print()
    print("  Layer 4 - Healing: Auto-recovery on failure via LLM")
    print("                      Demo: location_checker with typo 'Beiing'")
    print()
    print("  Layer 5 - Reflect: Task completion verification via LLM")
    print("                      Demo: quality check on all successful executions")
    print()
    print("  Layer 6 - Observe: Lifecycle logging (LogPlugin)")
    print("                      Demo: Hook events captured by HookManager")
    print()
    print("  Independent Mode: LLM picks tool + params from natural language")
    print("  Embedded Mode:    Direct execute() with precise plugin control")
    print()
    print("  Done!")


if __name__ == "__main__":
    main()
