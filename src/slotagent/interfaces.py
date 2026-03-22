# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
SlotAgent 核心接口定义。

本模块定义了 SlotAgent 的核心接口:
- PluginInterface: 插件抽象基类
- 相关异常类
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from slotagent.types import PluginContext, PluginResult


# =============================================================================
# 异常定义
# =============================================================================


class PluginError(Exception):
    """插件基础异常"""

    pass


class PluginExecutionError(PluginError):
    """插件执行异常"""

    pass


class PluginConfigError(PluginError):
    """插件配置异常"""

    pass


class PluginValidationError(PluginError):
    """插件验证异常"""

    pass


class ToolError(Exception):
    """工具基础异常"""

    pass


class ToolExecutionError(ToolError):
    """工具执行异常"""

    pass


class ToolNotFoundError(ToolError):
    """工具不存在"""

    pass


class ToolValidationError(ToolError):
    """工具参数验证异常"""

    pass


# =============================================================================
# 接口定义
# =============================================================================


class PluginInterface(ABC):
    """
    所有插件的抽象基类。

    插件是 SlotAgent 的核心扩展机制,每个插件负责特定层级的功能。
    所有自定义插件必须继承此类并实现 validate() 和 execute() 方法。

    Attributes:
        layer: 插件所属层级,必须是 'schema'/'guard'/'healing'/'reflect'/'observe' 之一
        plugin_id: 插件唯一标识,格式为 {layer}_{name}

    Contract:
        - 插件执行不应修改 context (context 是 frozen dataclass)
        - 同一 context 多次执行应返回相同结果 (幂等性,除非有外部状态)
        - 插件应该无状态,所有信息从 context 获取

    Examples:
        >>> class SchemaDefault(PluginInterface):
        ...     layer = 'schema'
        ...     plugin_id = 'schema_default'
        ...
        ...     def validate(self) -> bool:
        ...         return True
        ...
        ...     def execute(self, context: PluginContext) -> PluginResult:
        ...         # 实现验证逻辑
        ...         return PluginResult(success=True, data={'validated': True})
    """

    # 类属性 - 子类必须定义
    layer: ClassVar[str]  # 插件所属层级
    plugin_id: ClassVar[str]  # 插件唯一标识

    @abstractmethod
    def validate(self) -> bool:
        """
        验证插件配置是否有效。

        在插件注册时调用,确保插件配置正确。

        Returns:
            bool: True 表示配置有效,False 表示无效

        Raises:
            PluginConfigError: 配置无效时应抛出异常并说明原因

        Notes:
            - 此方法在插件注册时调用,不在执行时调用
            - 应检查插件依赖、配置参数等
        """
        pass

    @abstractmethod
    def execute(self, context: PluginContext) -> PluginResult:
        """
        执行插件逻辑。

        Args:
            context: 插件执行上下文,包含工具信息、参数、前序结果等

        Returns:
            PluginResult: 插件执行结果

        Raises:
            PluginExecutionError: 插件执行异常

        Contract:
            Precondition:
                - context 不为 None
                - context.layer == self.layer
                - context.params 已通过 Schema 验证 (对于 guard 及后续插件)

            Postcondition:
                - 返回值类型为 PluginResult
                - result.success 为 False 时,result.error 不为 None

            Invariant:
                - 插件执行不修改 context (context 是 frozen dataclass)
                - 同一 context 多次执行应返回相同结果 (幂等性)

        Examples:
            >>> def execute(self, context: PluginContext) -> PluginResult:
            ...     if not context.params.get('location'):
            ...         return PluginResult(
            ...             success=False,
            ...             error="参数 'location' 不能为空",
            ...             error_type="ValidationError",
            ...             should_continue=False
            ...         )
            ...     return PluginResult(success=True, data={'validated': True})
        """
        pass

    def __init_subclass__(cls, **kwargs):
        """
        子类初始化时的验证。

        确保子类定义了必需的类属性。
        """
        super().__init_subclass__(**kwargs)

        # 检查是否定义了 layer
        if not hasattr(cls, 'layer') or cls.layer is None:
            raise PluginConfigError(
                f"Plugin '{cls.__name__}' must define 'layer' class attribute"
            )

        # 检查是否定义了 plugin_id
        if not hasattr(cls, 'plugin_id') or cls.plugin_id is None:
            raise PluginConfigError(
                f"Plugin '{cls.__name__}' must define 'plugin_id' class attribute"
            )

        # 检查 layer 是否有效
        valid_layers = {'schema', 'guard', 'healing', 'reflect', 'observe'}
        if cls.layer not in valid_layers:
            raise PluginConfigError(
                f"Plugin '{cls.__name__}' has invalid layer '{cls.layer}'. "
                f"Must be one of: {valid_layers}"
            )
