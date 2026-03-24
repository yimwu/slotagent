# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
LLM 抽象层

提供统一的 LLM 接口,支持多种 LLM 提供商。
"""

from slotagent.llm.interface import LLMInterface, LLMMessage, LLMResponse
from slotagent.llm.mock_llm import MockLLM
from slotagent.llm.qwen_llm import QwenLLM

__all__ = [
    "LLMInterface",
    "LLMMessage",
    "LLMResponse",
    "MockLLM",
    "QwenLLM",
]
