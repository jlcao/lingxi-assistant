import logging
import json
import re
from typing import Dict, Optional, Any
from lingxi.core.llm_client import LLMClient
from lingxi.core.prompts import PromptTemplates


class TaskClassifier:
    """任务分类器，实现三级分类（trivial/simple/complex）"""

    def __init__(self, config: Dict[str, Any]):
        """初始化任务分类器

        Args:
            config: 系统配置
        """
        self.config = config
        self.llm_client = LLMClient(config)
        self.logger = logging.getLogger(__name__)

        classification_config = config.get("task_classification", {})
        self.strategy = classification_config.get("strategy", "llm_first")
        self.llm_confidence_threshold = classification_config.get("llm_confidence_threshold", 0.7)
        self.fallback_to_rule = classification_config.get("fallback_to_rule", True)

        self.logger.debug(f"初始化任务分类器，策略: {self.strategy}")

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
        history_text = PromptTemplates.format_history_context(history)
        
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

        response = self.llm_client.complete(prompt,task_level="simple")
        return self._parse_json_response(response)

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
