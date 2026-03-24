# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Mock LLM Implementation - 用于测试

提供可预设响应的 Mock LLM,用于单元测试
"""

from typing import Dict, List, Optional

from slotagent.llm.interface import LLMInterface, LLMMessage, LLMResponse


class MockLLM(LLMInterface):
    """
    Mock LLM 实现,用于快速单元测试

    支持预设响应规则,并记录调用历史。

    Examples:
        >>> mock_llm = MockLLM(responses={
        ...     'error': '{"analysis": "拼写错误", "fixed_params": {"city": "Beijing"}}',
        ...     'weather': '{"completed": true, "quality_score": 95}'
        ... })
        >>> messages = [LLMMessage(role="user", content="Fix this error")]
        >>> response = mock_llm.complete(messages)
        >>> print(response.content)  # 返回包含 'error' 关键词的预设响应
    """

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        初始化 Mock LLM

        Args:
            responses: 预设响应字典,格式为 {关键词: 响应内容}
                      当消息内容包含关键词时,返回对应响应
        """
        self.responses = responses or {}
        self.call_history: List[List[LLMMessage]] = []

    def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        模拟 LLM 调用,返回预设响应

        Args:
            messages: 消息列表
            temperature: 温度参数 (Mock 中忽略)
            max_tokens: 最大token数 (Mock 中忽略)

        Returns:
            预设的 LLM 响应
        """
        # 记录调用历史
        self.call_history.append(messages)

        # 匹配预设响应
        if messages:
            last_content = messages[-1].content
            for keyword, response in self.responses.items():
                if keyword in last_content:
                    return LLMResponse(content=response, model="mock")

        # 默认响应
        return LLMResponse(content="Mock response", model="mock")
