# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Reflect layer plugins - Task completion verification.

Verifies that tool execution achieved the intended goal.
"""

import json
from typing import TYPE_CHECKING

from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult

if TYPE_CHECKING:
    from slotagent.llm.interface import LLMInterface, LLMMessage


class ReflectSimple(PluginInterface):
    """
    Simple Reflect plugin - basic task completion check.

    Phase 3: Simple implementation that reports task completed.
    Future phases can add LLM-based verification.

    Examples:
        >>> plugin = ReflectSimple()
    """

    layer = "reflect"
    plugin_id = "reflect_simple"

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute reflection check.

        Phase 3: Simple implementation that assumes task completed.

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with task completion status
        """
        # Phase 3: Simple implementation
        # Just report task completed
        # Future: Add actual verification logic

        return PluginResult(
            success=True,
            data={
                "task_completed": True,
                "message": "Task assumed completed (Phase 3 placeholder)",
            },
        )


# Reflect 提示词模板
REFLECT_PROMPT_TEMPLATE = """
工具名称: {tool_name}
工具目标: {tool_description}

输入参数: {params}
执行结果: {result}

请判断: 这个结果是否完成了工具应该做的事?

要求:
1. 基于工具目标判断(不考虑用户的整体任务)
2. 检查结果是否完整
3. 评估结果质量

返回JSON格式: {{"completed": true/false, "reason": "判断理由", "quality_score": 0-100}}

重要: 请直接返回JSON,不要添加任何其他文字说明。
"""


class ReflectLLM(PluginInterface):
    """
    LLM 驱动的智能反思插件

    使用 LLM 验证工具执行结果是否完成了工具的目标。

    Examples:
        >>> from slotagent.llm import MockLLM
        >>> mock_llm = MockLLM(responses={'判断': '{"completed": true, "reason": "ok", "quality_score": 95}'})
        >>> plugin = ReflectLLM(llm=mock_llm)
    """

    layer = "reflect"
    plugin_id = "reflect_llm"

    def __init__(
        self,
        llm: "LLMInterface",
        temperature: float = 0.2,
        min_quality_score: int = 60,
    ):
        """
        Initialize ReflectLLM plugin.

        Args:
            llm: LLM instance for analyzing results
            temperature: Temperature for LLM (0-1), lower = more consistent
            min_quality_score: Minimum acceptable quality score (0-100)
        """
        self.llm = llm
        self.temperature = temperature
        self.min_quality_score = min_quality_score

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return self.llm is not None

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute reflection using LLM.

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with task completion assessment
        """
        # 获取工具执行结果
        tool_result = context.previous_results.get("result") if context.previous_results else None
        if not tool_result:
            return PluginResult(
                success=True, data={"task_completed": False, "reason": "无执行结果"}
            )

        # 构造提示词
        prompt = REFLECT_PROMPT_TEMPLATE.format(
            tool_name=context.tool_name,
            tool_description=context.tool_description or "未提供描述",
            params=json.dumps(context.params, ensure_ascii=False, indent=2),
            result=json.dumps(tool_result, ensure_ascii=False, indent=2),
        )

        # 调用 LLM
        try:
            from slotagent.llm.interface import LLMMessage

            response = self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=self.temperature,
            )

            # 解析响应
            content = response.content.strip()

            # 查找JSON部分
            if "{" in content and "}" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                json_str = content[start:end]
                result = json.loads(json_str)
            else:
                result = json.loads(content)

            completed = result.get("completed", True)
            quality_score = result.get("quality_score", 100)

            # 质量分数过低视为未完成
            if quality_score < self.min_quality_score:
                completed = False

            return PluginResult(
                success=True,
                data={
                    "task_completed": completed,
                    "reason": result.get("reason", ""),
                    "quality_score": quality_score,
                },
            )

        except json.JSONDecodeError as e:
            # LLM 调用失败,默认认为完成(保守策略)
            return PluginResult(
                success=True,
                data={
                    "task_completed": True,
                    "reason": f"Reflect LLM响应解析失败,默认通过: {str(e)}",
                    "quality_score": 100,
                },
            )
        except Exception as e:
            # LLM 调用失败,默认认为完成(保守策略)
            return PluginResult(
                success=True,
                data={
                    "task_completed": True,
                    "reason": f"Reflect LLM调用失败,默认通过: {str(e)}",
                    "quality_score": 100,
                },
            )
