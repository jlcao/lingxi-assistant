"""任务分类模块

独立的任务分类器，通过依赖注入实现解耦
"""

import logging
import json
import re
from typing import Dict, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from lingxi.core.interfaces import ILLMClient


class TaskClassifier:
    """任务分类器，实现三级分类（trivial/simple/complex）"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, config: Dict[str, Any]):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any], llm_client: Optional['ILLMClient'] = None):
        """初始化任务分类器

        Args:
            config: 系统配置
            llm_client: LLM客户端（可选，延迟注入）
        """
        self.config = config
        self._llm_client = llm_client
        self.logger = logging.getLogger(__name__)

        classification_config = config.get("task_classification", {})
        self.strategy = classification_config.get("strategy", "llm_first")
        self.llm_confidence_threshold = classification_config.get("llm_confidence_threshold", 0.7)
        self.fallback_to_rule = classification_config.get("fallback_to_rule", True)

        self.logger.debug(f"初始化任务分类器，策略: {self.strategy}")
    
    def set_llm_client(self, llm_client: 'ILLMClient') -> None:
        """设置LLM客户端（依赖注入）
        
        Args:
            llm_client: LLM客户端实例
        """
        self._llm_client = llm_client
        self.logger.debug("LLM客户端已注入")
    
    @property
    def llm_client(self) -> 'ILLMClient':
        """获取LLM客户端"""
        if self._llm_client is None:
            raise RuntimeError("LLM客户端未设置，请先调用 set_llm_client() 方法")
        return self._llm_client

    def classify(self, task_text: str, history: Optional[list] = None) -> Dict[str, Any]:
        """分类用户任务

        Args:
            task_text: 任务文本
            history: 历史对话上下文

        Returns:
            包含任务级别、置信度和理由的字典
        """
        self.logger.debug(f"分类任务: {task_text}")
        if history:
            self.logger.debug(f"历史上下文: {len(history)} 条")

        if self.strategy == "llm_first":
            return self._llm_first_classify(task_text, history)
        elif self.strategy == "rule_first":
            return self._rule_first_classify(task_text, history)
        else:
            return self._llm_first_classify(task_text, history)

    def _llm_first_classify(self, task_text: str, history: Optional[list] = None) -> Dict[str, Any]:
        """优先使用LLM分类

        Args:
            task_text: 任务文本
            history: 历史对话上下文

        Returns:
            分类结果
        """
        try:
            llm_result = self._llm_classify(task_text, history)
            if llm_result["confidence"] >= self.llm_confidence_threshold:
                self.logger.debug(f"LLM分类结果: {llm_result}")
                return llm_result
        except Exception as e:
            self.logger.warning(f"LLM分类失败: {e}")

        if self.fallback_to_rule:
            self.logger.debug("使用规则fallback")
            return self._rule_classify(task_text)
        else:
            return {"level": "simple", "confidence": 0.5, "reason": "LLM分类失败且未启用规则fallback"}

    def _rule_first_classify(self, task_text: str, history: Optional[list] = None) -> Dict[str, Any]:
        """优先使用规则分类

        Args:
            task_text: 任务文本
            history: 历史对话上下文

        Returns:
            分类结果
        """
        rule_result = self._rule_classify(task_text)
        if rule_result["confidence"] >= 0.8:
            return rule_result

        try:
            llm_result = self._llm_classify(task_text, history)
            self.logger.debug(f"LLM分类结果: {llm_result}")
            return llm_result
        except Exception as e:
            self.logger.warning(f"LLM分类失败: {e}")
            return rule_result

    def _llm_classify(self, task_text: str, history: Optional[list] = None) -> Dict[str, Any]:
        """使用LLM进行分类

        Args:
            task_text: 任务文本
            history: 历史对话上下文

        Returns:
            分类结果
        """
        history_text = self._format_history_context(history)
        
        prompt = f"""你是任务分类器，将用户请求分为三级：
trivial：无需工具，直接回答（如问候、简单问答、闲聊）
simple：单一步骤、单工具调用（如查天气、翻译、简单文件读取）
complex：多步骤、多工具调用、需要多次交互或数据处理（如旅行规划、数据分析、读取并处理Excel、文件操作后处理数据）

重要判断标准：
- 如果任务需要读取文件后对数据进行处理（排序、筛选、统计等），必须是 complex
- 如果任务需要多个步骤完成，必须是 complex
- 如果任务只是简单查询或翻译，是 simple
- 如果任务只是问候或闲聊，是 trivial

输出JSON格式：
{{"level": "trivial|simple|complex", "confidence": 0.0-1.0, "reason": "理由"}}
{history_text}

用户请求：{task_text}
"""

        response = self.llm_client.complete(prompt, task_level="simple")
        return self._parse_json_response(response)
    
    def _format_history_context(self, history: Optional[list] = None) -> str:
        """格式化历史上下文
        
        Args:
            history: 历史对话列表
            
        Returns:
            格式化后的上下文字符串
        """
        if not history:
            return ""
        
        context_lines = []
        for item in history[-5:]:  # 只取最近5条
            if isinstance(item, dict):
                role = item.get("role", "")
                content = item.get("content", "")
                if role and content:
                    context_lines.append(f"{role}: {content}")
        
        if context_lines:
            return "\n".join(context_lines)
        return ""

    def _rule_classify(self, task_text: str) -> Dict[str, Any]:
        """使用规则进行分类

        Args:
            task_text: 任务文本

        Returns:
            分类结果
        """
        task_text_lower = task_text.lower()

        trivial_keywords = ["你好", "谢谢", "再见", "是谁", "什么是", "hello", "hi", "谢谢", "再见"]
        complex_keywords = ["规划", "分析", "对比", "总结", "多步骤", "plan", "analyze", "compare", "summarize", 
                        "读取", "排序", "筛选", "统计", "处理", "解析", "输出", "倒序", "升序", "excel", "xlsx", "csv", "数据"]

        if any(kw in task_text for kw in trivial_keywords):
            return {"level": "trivial", "confidence": 0.8, "reason": "规则匹配：问候/闲聊类"}
        elif any(kw in task_text for kw in complex_keywords):
            return {"level": "complex", "confidence": 0.7, "reason": "规则匹配：复杂任务关键词"}
        else:
            return {"level": "simple", "confidence": 0.6, "reason": "规则默认：单步骤任务"}

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应

        Args:
            response: LLM响应

        Returns:
            解析后的字典
        """
        try:
            json_match = re.search(r'\{[^}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)

                if "level" in result and result["level"] in ["trivial", "simple", "complex"]:
                    return {
                        "level": result["level"],
                        "confidence": float(result.get("confidence", 0.5)),
                        "reason": result.get("reason", "LLM分类")
                    }
        except Exception as e:
            self.logger.error(f"解析JSON响应失败: {e}")

        return {"level": "simple", "confidence": 0.5, "reason": "解析失败，默认simple"}
