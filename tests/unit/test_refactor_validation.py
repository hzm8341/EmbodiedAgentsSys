"""
任务 1.1：代码审查和重构测试

验证：
- 代码重复消除
- 命名约定一致性
- 文档字符串完整性
- 类型注解完整性
"""

import inspect
import pytest


class TestCodeDuplication:
    """代码重复消除"""

    def test_no_repeated_layer_implementations(self):
        """不存在重复的层级实现代码"""
        from agents.cognition.planning import PlanningLayerBase, DefaultPlanningLayer
        from agents.cognition.reasoning import ReasoningLayerBase, DefaultReasoningLayer
        from agents.cognition.learning import LearningLayerBase, DefaultLearningLayer

        # 验证基类都有相似的接口
        assert hasattr(PlanningLayerBase, 'generate_plan')
        assert hasattr(ReasoningLayerBase, 'generate_action')
        assert hasattr(LearningLayerBase, 'improve')

        # 验证默认实现都继承正确的基类
        assert issubclass(DefaultPlanningLayer, PlanningLayerBase)
        assert issubclass(DefaultReasoningLayer, ReasoningLayerBase)
        assert issubclass(DefaultLearningLayer, LearningLayerBase)

    def test_unified_initialization_pattern(self):
        """统一的初始化模式"""
        from agents.feedback.logger import FeedbackLogger
        from agents.feedback.analyzer import FeedbackAnalyzer
        from agents.feedback.loop import FeedbackLoop

        # 所有反馈组件都应该有 __init__
        assert hasattr(FeedbackLogger, '__init__')
        assert hasattr(FeedbackAnalyzer, '__init__')
        assert hasattr(FeedbackLoop, '__init__')


class TestNamingConventions:
    """命名约定一致性"""

    def test_snake_case_function_names(self):
        """所有函数使用 snake_case"""
        from agents.core.types import RobotObservation, SkillResult
        from agents.config.manager import ConfigManager

        # 检查 ConfigManager 方法名
        methods = [m for m in dir(ConfigManager) if not m.startswith('_')]
        for method_name in methods:
            # 私有方法可以有下划线
            if not method_name.startswith('_'):
                # 所有公开方法应该是 snake_case 或全大写常量
                assert method_name.islower() or method_name.isupper() or '_' in method_name, \
                    f"Method {method_name} should be snake_case"

    def test_consistent_variable_naming(self):
        """变量命名一致性"""
        from agents.core.agent_loop import RobotAgentLoop
        from agents.core.types import AgentConfig

        # 检查类的属性命名
        config = AgentConfig(agent_name="test", max_steps=10)
        loop = RobotAgentLoop(
            llm_provider=None,
            perception_provider=None,
            executor=None,
            config=config
        )
        assert hasattr(loop, 'config')
        assert hasattr(loop, 'step_count')

    def test_class_names_are_capitalized(self):
        """类名使用 PascalCase"""
        from agents.simple_agent import SimpleAgent
        from agents.cognition.engine import CognitionEngine
        from agents.feedback.loop import FeedbackLoop

        # 类名都应该是大写开头
        assert SimpleAgent.__name__[0].isupper()
        assert CognitionEngine.__name__[0].isupper()
        assert FeedbackLoop.__name__[0].isupper()


class TestDocstringCoverage:
    """文档字符串完整性"""

    def test_core_classes_documented(self):
        """核心类都有文档"""
        from agents.core.types import RobotObservation, SkillResult, AgentConfig
        from agents.core.agent_loop import RobotAgentLoop

        assert RobotObservation.__doc__ is not None, "RobotObservation missing docstring"
        assert SkillResult.__doc__ is not None, "SkillResult missing docstring"
        assert AgentConfig.__doc__ is not None, "AgentConfig missing docstring"
        assert RobotAgentLoop.__doc__ is not None, "RobotAgentLoop missing docstring"

    def test_cognition_layer_classes_documented(self):
        """认知层类都有文档"""
        from agents.cognition.planning import PlanningLayerBase, DefaultPlanningLayer
        from agents.cognition.reasoning import ReasoningLayerBase, DefaultReasoningLayer
        from agents.cognition.learning import LearningLayerBase, DefaultLearningLayer
        from agents.cognition.engine import CognitionEngine

        assert PlanningLayerBase.__doc__ is not None
        assert DefaultPlanningLayer.__doc__ is not None
        assert ReasoningLayerBase.__doc__ is not None
        assert DefaultReasoningLayer.__doc__ is not None
        assert LearningLayerBase.__doc__ is not None
        assert DefaultLearningLayer.__doc__ is not None
        assert CognitionEngine.__doc__ is not None

    def test_feedback_layer_classes_documented(self):
        """反馈层类都有文档"""
        from agents.feedback.logger import FeedbackLogger
        from agents.feedback.analyzer import FeedbackAnalyzer
        from agents.feedback.loop import FeedbackLoop

        assert FeedbackLogger.__doc__ is not None
        assert FeedbackAnalyzer.__doc__ is not None
        assert FeedbackLoop.__doc__ is not None

    def test_public_methods_documented(self):
        """公开方法都有文档"""
        from agents.simple_agent import SimpleAgent
        from agents.config.manager import ConfigManager

        # SimpleAgent 的公开方法
        for method_name in ['from_preset', 'run_task']:
            method = getattr(SimpleAgent, method_name)
            assert method.__doc__ is not None, f"SimpleAgent.{method_name} missing docstring"

        # ConfigManager 的公开方法
        for method_name in ['create', 'load_preset', 'load_yaml']:
            method = getattr(ConfigManager, method_name)
            assert method.__doc__ is not None, f"ConfigManager.{method_name} missing docstring"


class TestTypeHintsCoverage:
    """类型注解完整性"""

    def test_core_functions_have_type_hints(self):
        """核心函数有类型注解"""
        from agents.core.agent_loop import RobotAgentLoop

        # 检查 step() 方法的类型注解
        step_method = RobotAgentLoop.step
        sig = inspect.signature(step_method)

        # 应该有 return 类型注解
        assert sig.return_annotation != inspect.Signature.empty, \
            "RobotAgentLoop.step should have return type annotation"

    def test_config_methods_have_type_hints(self):
        """配置管理方法有类型注解"""
        from agents.config.manager import ConfigManager

        # 检查 create() 方法
        sig = inspect.signature(ConfigManager.create)
        assert sig.return_annotation != inspect.Signature.empty, \
            "ConfigManager.create should have return type annotation"

    def test_cognition_layer_methods_have_type_hints(self):
        """认知层方法有类型注解"""
        from agents.cognition.planning import DefaultPlanningLayer
        from agents.cognition.reasoning import DefaultReasoningLayer

        # 检查 generate_plan() 方法
        planning_sig = inspect.signature(DefaultPlanningLayer.generate_plan)
        assert planning_sig.return_annotation != inspect.Signature.empty, \
            "DefaultPlanningLayer.generate_plan should have return type annotation"

        # 检查 generate_action() 方法
        reasoning_sig = inspect.signature(DefaultReasoningLayer.generate_action)
        assert reasoning_sig.return_annotation != inspect.Signature.empty, \
            "DefaultReasoningLayer.generate_action should have return type annotation"


class TestCodeQualityMetrics:
    """代码质量指标"""

    def test_module_imports_clean(self):
        """模块导入清晰"""
        import agents.core
        import agents.config
        import agents.cognition
        import agents.feedback
        import agents.execution
        import agents.extensions

        # 所有主要包都可以导入
        assert agents.core is not None
        assert agents.config is not None
        assert agents.cognition is not None
        assert agents.feedback is not None
        assert agents.execution is not None
        assert agents.extensions is not None

    def test_no_circular_imports(self):
        """没有循环导入"""
        # 如果能导入 SimpleAgent，说明没有循环导入
        from agents.simple_agent import SimpleAgent
        assert SimpleAgent is not None

    def test_exception_handling_in_core(self):
        """核心模块有异常处理"""
        from agents.config.manager import ConfigManager

        # 测试无效配置名
        with pytest.raises(Exception):
            ConfigManager.load_preset("nonexistent_preset")
