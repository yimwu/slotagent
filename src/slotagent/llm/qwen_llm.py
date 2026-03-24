# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Qwen LLM Implementation - 通义千问适配器

使用 OpenAI 兼容接口调用通义千问模型
"""

import os
from typing import List, Optional

import requests

from slotagent.llm.interface import LLMInterface, LLMMessage, LLMResponse


class QwenLLM(LLMInterface):
    """
    通义千问 LLM 适配器

    使用 OpenAI 兼容接口调用通义千问模型。

    Examples:
        >>> # 从环境变量读取 API key
        >>> llm = QwenLLM()
        >>>
        >>> # 或显式提供 API key
        >>> llm = QwenLLM(api_key="your-key-here")
        >>>
        >>> messages = [LLMMessage(role="user", content="Hello")]
        >>> response = llm.complete(messages)
        >>> print(response.content)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://coding.dashscope.aliyuncs.com/v1",
        model: str = "qwen3-coder-next",
        timeout: int = 60,
    ):
        """
        初始化通义千问 LLM

        Args:
            api_key: API密钥,默认从环境变量 DASHSCOPE_PLAN_API_KEY 读取
            base_url: API基础URL
            model: 模型名称
            timeout: 请求超时时间(秒),默认60秒

        Raises:
            ValueError: 如果未提供 API key 且环境变量未设置
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_PLAN_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key not provided and DASHSCOPE_PLAN_API_KEY environment variable not set"
            )

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        调用通义千问 API

        Args:
            messages: 消息列表
            temperature: 温度参数(0-1)
            max_tokens: 最大token数

        Returns:
            LLM 响应

        Raises:
            requests.HTTPError: API 调用失败
            KeyError: 响应格式不符合预期
        """
        # 转换消息格式
        api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        # 构造请求
        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # 调用 API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

        response.raise_for_status()
        data = response.json()

        # 解析响应
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=self.model,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )
