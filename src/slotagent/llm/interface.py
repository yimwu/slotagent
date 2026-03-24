# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
LLM Interface - 统一的 LLM 抽象接口

支持多种 LLM 提供商(GPT-4, Claude, 通义千问等)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class LLMMessage:
    """
    LLM 消息格式

    Attributes:
        role: 消息角色 ('system', 'user', 'assistant')
        content: 消息内容
    """

    role: str
    content: str


@dataclass
class LLMResponse:
    """
    LLM 响应

    Attributes:
        content: 响应内容
        model: 使用的模型名称
        usage: Token 使用统计 (可选)
    """

    content: str
    model: str
    usage: Optional[Dict[str, int]] = None


class LLMInterface(ABC):
    """
    LLM 抽象接口 - 支持多种 LLM 提供商

    设计原则:
    - 统一接口,隔离具体实现
    - 支持 GPT-4/Claude/通义千问 等
    - 简单直接,不过度设计

    Examples:
        >>> llm = SomeLLMImpl()
        >>> messages = [LLMMessage(role="user", content="Hello")]
        >>> response = llm.complete(messages)
        >>> print(response.content)
    """

    @abstractmethod
    def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        调用 LLM 生成回复

        Args:
            messages: 消息列表
            temperature: 温度参数(0-1), 越低越确定性
            max_tokens: 最大token数 (可选)

        Returns:
            LLM 响应

        Raises:
            Exception: LLM 调用失败时抛出异常
        """
        pass
