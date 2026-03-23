# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Healing layer plugins - Auto-recovery on failure.

Provides retry mechanisms for failed tool executions.
"""

import json
from typing import TYPE_CHECKING

from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult

if TYPE_CHECKING:
    from slotagent.llm.interface import LLMInterface, LLMMessage


class HealingRetry(PluginInterface):
    """
    Healing plugin with retry capability.

    Phase 3 implementation: Simple retry tracking.
    Phase 5 will add actual retry execution with CoreScheduler integration.

    Examples:
        >>> plugin = HealingRetry(max_retries=3, initial_delay=1.0)
    """

    layer = "healing"
    plugin_id = "healing_retry"

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0):
        """
        Initialize HealingRetry plugin.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries (seconds)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute healing logic.

        Phase 3: Simple implementation that reports not recovered.
        Actual retry logic will be implemented in later phases with
        CoreScheduler integration.

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with recovery status
        """
        # Phase 3: Simple implementation
        # Just report that healing was attempted but not recovered
        # Actual retry implementation requires CoreScheduler integration

        return PluginResult(
            success=True,
            data={
                "recovered": False,
                "max_retries": self.max_retries,
                "retry_count": 0,
                "message": "Healing attempted (Phase 3 placeholder)",
            },
        )


# Healing 提示词模板
HEALING_PROMPT_TEMPLATE = """
工具名称: {tool_name}
工具目标: {tool_description}

原始参数: {params}
执行错误: {error}

请分析错误原因,并提供修复后的参数。

要求:
1. 只修改导致错误的参数
2. 保持其他参数不变
3. 返回JSON格式: {{"analysis": "错误原因分析", "fixed_params": {{修复后的完整参数}}}}

重要: 请直接返回JSON,不要添加任何其他文字说明。
"""


class HealingLLM(PluginInterface):
    """
    LLM 驱动的智能自愈插件

    使用 LLM 分析工具执行错误,智能修复参数并重试。

    Examples:
        >>> from slotagent.llm import MockLLM
        >>> mock_llm = MockLLM(responses={'error': '{"analysis": "fix", "fixed_params": {}}'})
        >>> plugin = HealingLLM(llm=mock_llm)
    """

    layer = "healing"
    plugin_id = "healing_llm"

    def __init__(
        self,
        llm: "LLMInterface",
        max_retries: int = 2,
        temperature: float = 0.3,
    ):
        """
        Initialize HealingLLM plugin.

        Args:
            llm: LLM instance for analyzing errors
            max_retries: Maximum number of retry attempts
            temperature: Temperature for LLM (0-1), lower = more deterministic
        """
        self.llm = llm
        self.max_retries = max_retries
        self.temperature = temperature

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return self.llm is not None

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute healing logic using LLM.

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with recovery status and fixed parameters
        """
        # 获取错误信息
        error_info = context.previous_results.get("error") if context.previous_results else None
        if not error_info:
            return PluginResult(
                success=True, data={"recovered": False, "reason": "No error to heal"}
            )

        # 构造提示词
        prompt = HEALING_PROMPT_TEMPLATE.format(
            tool_name=context.tool_name,
            tool_description=context.tool_description or "未提供描述",
            params=json.dumps(context.params, ensure_ascii=False, indent=2),
            error=str(error_info),
        )

        # 调用 LLM
        try:
            from slotagent.llm.interface import LLMMessage

            response = self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=self.temperature,
            )

            # 解析响应
            # 尝试提取JSON (LLM可能返回包含解释的文本)
            content = response.content.strip()

            # 查找JSON部分
            if "{" in content and "}" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                json_str = content[start:end]
                result = json.loads(json_str)
            else:
                result = json.loads(content)

            fixed_params = result.get("fixed_params")

            if fixed_params:
                return PluginResult(
                    success=True,
                    should_continue=True,  # 继续重试
                    data={
                        "recovered": True,
                        "fixed_params": fixed_params,
                        "analysis": result.get("analysis", ""),
                    },
                )
            else:
                return PluginResult(
                    success=False,
                    data={"recovered": False, "reason": "LLM无法修复参数"},
                )

        except json.JSONDecodeError as e:
            return PluginResult(
                success=False,
                error=f"Healing LLM响应解析失败: {str(e)}, Response: {response.content[:200]}",
                data={"recovered": False},
            )
        except Exception as e:
            return PluginResult(
                success=False,
                error=f"Healing LLM调用失败: {str(e)}",
                data={"recovered": False},
            )
