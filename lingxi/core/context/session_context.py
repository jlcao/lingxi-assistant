import logging
import sqlite3
import json
import time
import re
from typing import List, Dict, Optional, Any, Union
from lingxi.core.session.session_models import Task,Step
from dataclasses import dataclass, field
from enum import Enum
from lingxi.utils.config import get_config


class ContentType(Enum):
    """内容类型枚举"""
    USER_INPUT = "user_input" # 用户输入
    ASSISTANT_RESPONSE = "assistant_response"  # 助手回复
    TOOL_CALL = "tool_call"   # 工具调用
    TOOL_RESULT = "tool_result"  # 工具调用结果
    SYSTEM_MESSAGE = "system_message"  # 系统消息
    THINKING = "thinking"  # 思考状态


@dataclass
class ContextMessage:
    """上下文消息单元"""
    id: str
    role: str
    content: str #原始内容
    content_type: ContentType
    token_count: int
    task_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    is_compressed: bool = False   #是否压缩
    summary: Optional[str] = None  #压缩后的内容
    metadata: Dict = field(default_factory=dict)


class SessionContext:
    """会话上下文对象，封装会话的所有上下文信息"""
    

    def __init__(self, session_id: str):
        """初始化会话上下文

        Args:
            session_id: 会话ID
        """
        self.session_id = session_id
        self.messages: List[ContextMessage] = []
        self.current_task_id: Optional[str] = None
        self.token_usage = 0
        self.soul_prompt: Optional[str] = None

        self.config = get_config()

        context_config = self.config.get("context_management", {})
        token_budget = context_config.get("token_budget", {})
        self.max_tokens = token_budget.get("max_tokens", 8000)
        self.compression_trigger = token_budget.get("compression_trigger", 0.7)
        self.critical_threshold = token_budget.get("critical_threshold", 0.9)

        retention_config = context_config.get("retention", {})
        self.user_input_keep_turns = retention_config.get("user_input_keep_turns", 10)
        self.tool_result_keep_turns = retention_config.get("tool_result_keep_turns", 5)
        self.task_boundary_archive = retention_config.get("task_boundary_archive", True)

        compression_config = context_config.get("compression", {})
        self.compression_strategy = compression_config.get("strategy", "hybrid")
        self.summary_ratio = compression_config.get("summary_ratio", 0.3)
        self.enable_llm_summary = compression_config.get("enable_llm_summary", True)
        self.preserve_entities = compression_config.get("preserve_entities", True)

        long_term_config = context_config.get("long_term_memory", {})
        self.enable_long_term_memory = long_term_config.get("enabled", True)

        if self.enable_long_term_memory:
            from lingxi.core.context.long_term_memory import LongTermMemory
            from pathlib import Path
            
            # 处理数据库路径：如果是相对路径，转换为相对于用户目录的绝对路径
            db_path = long_term_config.get("db_path", "data/long_term_memory.db")
            if not Path(db_path).is_absolute():
                # 相对路径，转换为用户目录下的绝对路径
                user_lingxi_dir = Path.home() / ".lingxi"
                db_path = str(user_lingxi_dir / db_path)
            
            self.long_term_memory = LongTermMemory(
                db_path=db_path,
                vector_dim=long_term_config.get("vector_dim", 384)
            )

        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"初始化上下文管理器，会话ID: {session_id}")

   
    def add_history(self,history:List[Task]):
        """添加历史会话到上下文管理器

        Args:
            history: 历史会话消息列表
        """
        
        for task in history:
            # 添加用户输入
            self.add_message("assistant", f"** 历史对话 task_id:{task.task_id}开始 ** ========分隔符", ContentType.SYSTEM_MESSAGE, task.task_id)
            self.add_message("user", task.user_input, ContentType.USER_INPUT, task.task_id)
            self.add_message("assistant", "执行步骤:", ContentType.SYSTEM_MESSAGE, task.task_id)
            #for step in task.steps:
               # if step.skill_call != "" and step.status == "completed":
                    #self.add_message("assistant", step.thought, ContentType.THINKING, step.step_index)
                    #self.add_message("assistant",f"调用工具:{step.skill_call}", ContentType.TOOL_CALL, step.step_index)
                    #self.add_message("assistant",f"step {step.step_index}, 工具调用:{step.skill_call},结果:{step.result}", ContentType.TOOL_RESULT, step.step_index)
            # 添加助手最终回复
            self.add_message("assistant", f"最终回复：{task.result}",  ContentType.ASSISTANT_RESPONSE, task.task_id)
            self.add_message("assistant", "** 历史对话 task_id:{task.task_id}结束 ** ========分隔符", ContentType.SYSTEM_MESSAGE, task.task_id)
            

    def add_context_item(self,role:str,content:str):
        """添加上下文项

        Args:
            role: 角色（user/assistant/tool/system）
            content: 内容
        """
        self.add_message(role, content, ContentType.SYSTEM_MESSAGE)
    
    

    def add_message(self, role: str, content: str,
                   content_type: ContentType = None,
                   task_id: str = None,
                   metadata: Dict = None) -> ContextMessage:
        """添加消息到上下文

        Args:
            role: 角色（user/assistant/tool/system）
            content: 内容
            content_type: 内容类型
            task_id: 任务ID
            metadata: 元数据

        Returns:
            创建的上下文消息
        """
        if not isinstance(content, Dict):
            content = str(content)
        
        token_count = len(content) // 4

        message = ContextMessage(
            id=f"msg_{int(time.time() * 1000)}_{len(self.messages)}",
            role=role,
            content=content,
            content_type=content_type or self._infer_content_type(role, content),
            token_count=token_count,
            task_id=task_id or self.current_task_id,
            metadata=metadata or {}
        )

        self.messages.append(message)
        self.token_usage += token_count

        if self._should_compress():
            self.compress()

        return message

    def _should_compress(self) -> bool:
        """判断是否需要压缩"""
        usage_ratio = self.token_usage / self.max_tokens
        return usage_ratio >= self.compression_trigger

    def compress(self, strategy: str = None) -> Dict[str, Any]:
        """执行上下文压缩

        Args:
            strategy: 压缩策略（hybrid/summary/sliding_window）

        Returns:
            压缩统计信息
        """
        strategy = strategy or self.compression_strategy

        stats = {
            "before_tokens": self.token_usage,
            "compressed_count": 0,
            "archived_count": 0
        }

        self.logger.debug(f"触发上下文压缩，策略: {strategy}")

        if strategy == "hybrid":
            stats.update(self._compress_thinking())
            stats.update(self._compress_tool_results())
            stats.update(self._archive_old_tasks())
            stats.update(self._sliding_window())

        elif strategy == "summary":
            stats.update(self._llm_summary())

        elif strategy == "sliding_window":
            stats.update(self._sliding_window())

        stats["after_tokens"] = self.token_usage
        stats["compression_ratio"] = 1 - (stats["after_tokens"] / stats["before_tokens"]) if stats["before_tokens"] > 0 else 0

        self.logger.debug(f"压缩完成，节省token: {stats['before_tokens'] - stats['after_tokens']} ({stats['compression_ratio']:.1%})")

        return stats

    def compress_context(self, strategy: str = None) -> Dict[str, Any]:
        """执行上下文压缩（compress 的别名）

        Args:
            strategy: 压缩策略（hybrid/summary/sliding_window）

        Returns:
            压缩统计信息
        """
        return self.compress(strategy=strategy)

    def _compress_thinking(self) -> Dict[str, Any]:
        """压缩策略1：移除模型推理过程"""
        compressed_count = 0
        removed_tokens = 0

        for msg in self.messages:
            if msg.content_type == ContentType.THINKING:
                msg.is_compressed = True
                msg.summary = "[推理过程已压缩]"
                removed_tokens += msg.token_count
                compressed_count += 1

        self.messages = [m for m in self.messages if m.content_type != ContentType.THINKING]
        self.token_usage -= removed_tokens

        return {"thinking_compressed": compressed_count, "tokens_freed": removed_tokens}

    def _compress_tool_results(self) -> Dict[str, Any]:
        """压缩策略2：摘要工具调用结果"""
        compressed_count = 0
        tokens_freed = 0

        tool_results = [m for m in self.messages if m.content_type == ContentType.TOOL_RESULT]

        if len(tool_results) > self.tool_result_keep_turns:
            to_compress = tool_results[:-self.tool_result_keep_turns]

            for msg in to_compress:
                if not msg.is_compressed:
                    if self.enable_llm_summary:
                        msg.summary = self._summarize_with_llm(msg.content)
                    else:
                        msg.summary = self._truncate_summary(msg.content)

                    msg.is_compressed = True
                    tokens_freed += int(msg.token_count * (1 - self.summary_ratio))
                    compressed_count += 1

        return {"tool_results_compressed": compressed_count, "tokens_freed": tokens_freed}

    def _archive_old_tasks(self) -> Dict[str, Any]:
        """压缩策略3：归档已完成任务的历史"""
        archived_count = 0
        tokens_freed = 0

        if not self.task_boundary_archive or not self.enable_long_term_memory:
            return {"tasks_archived": 0, "tokens_freed": 0}

        current_task_msgs = [m for m in self.messages if m.task_id == self.current_task_id]
        old_task_msgs = [m for m in self.messages if m.task_id and m.task_id != self.current_task_id]

        if old_task_msgs:
            task_summary = self._generate_task_summary(old_task_msgs)

            self.long_term_memory.store(
                task_id=old_task_msgs[0].task_id,
                summary=task_summary,
                messages=old_task_msgs,
                session_id=self.session_id
            )

            archived_count = len(old_task_msgs)
            tokens_freed = sum(m.token_count for m in old_task_msgs)
            self.messages = current_task_msgs + [m for m in self.messages if not m.task_id]
            self.token_usage -= tokens_freed

        return {"tasks_archived": archived_count, "tokens_freed": tokens_freed}

    def _sliding_window(self) -> Dict[str, Any]:
        """压缩策略4：滑动窗口保留"""
        tokens_freed = 0

        user_inputs = [m for m in self.messages if m.content_type == ContentType.USER_INPUT]

        if len(user_inputs) > self.user_input_keep_turns:
            to_remove = user_inputs[:-self.user_input_keep_turns]
            for msg in to_remove:
                if not msg.is_compressed:
                    msg.is_compressed = True
                    msg.summary = "[历史对话已归档]"
                    tokens_freed += msg.token_count

            self.token_usage -= tokens_freed

        return {"sliding_window_applied": True, "tokens_freed": tokens_freed}

    def _llm_summary(self) -> Dict[str, Any]:
        """LLM智能摘要"""
        compressed_count = 0
        tokens_freed = 0

        for msg in self.messages:
            if not msg.is_compressed and msg.content_type in [ContentType.ASSISTANT_RESPONSE, ContentType.TOOL_RESULT]:
                msg.summary = self._summarize_with_llm(msg.content)
                msg.is_compressed = True
                tokens_freed += int(msg.token_count * (1 - self.summary_ratio))
                compressed_count += 1

        return {"llm_summary_compressed": compressed_count, "tokens_freed": tokens_freed}

    def _summarize_with_llm(self, content: str) -> str:
        """使用LLM智能摘要"""
        max_length = int(len(content) * self.summary_ratio)
        if max_length < 50:
            max_length = 50

        if self.preserve_entities:
            entities = self._extract_entities(content)
            entity_str = ", ".join(entities) if entities else ""
            return f"[摘要] {content[:max_length]}... 关键实体: {entity_str}"

        return f"[摘要] {content[:max_length]}..."

    def _truncate_summary(self, content: str, max_length: int = 200) -> str:
        """截断摘要"""
        if len(content) <= max_length:
            return content

        if self.preserve_entities:
            entities = self._extract_entities(content)
            entity_str = ", ".join(entities) if entities else ""
            return f"[摘要] {content[:max_length]}... 关键实体: {entity_str}"

        return f"[摘要] {content[:max_length]}..."

    def _generate_task_summary(self, messages: List[ContextMessage]) -> str:
        """生成任务摘要"""
        user_inputs = [m.content for m in messages if m.content_type == ContentType.USER_INPUT]
        tool_calls = [m.metadata.get("skill_id") for m in messages if m.content_type == ContentType.TOOL_CALL]
        results = [m.content for m in messages if m.content_type == ContentType.TOOL_RESULT]

        summary = f"任务完成：{user_inputs[0] if user_inputs else '未知'}\n"
        if tool_calls:
            summary += f"调用工具：{', '.join(set(tool_calls))}\n"
        if results:
            summary += f"关键结果：{results[0][:100] if results else '无'}"

        return summary

    def _extract_entities(self, text: str) -> List[str]:
        """提取关键实体"""
        entities = []
        entities.extend(re.findall(r'"([^"]+)"', text))
        entities.extend(re.findall(r'\d{4}-\d{2}-\d{2}', text))
        entities.extend(re.findall(r'\d{2}:\d{2}', text))
        entities.extend(re.findall(r'\d+\.?\d*', text)[:5])

        return list(set(entities))

    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """获取发送给LLM的上下文"""
        context = []

        for msg in self.messages:
            if msg.is_compressed and msg.summary:
                context.append({
                    "role": msg.role,
                    "content_type": msg.content_type,
                    "content": msg.summary
                })
            else:
                context.append({
                    "role": msg.role,
                    "content_type": msg.content_type,
                    "content": msg.content
                })

        return context

    def get_history_context(self) -> str:
        """构建历史上下文
        """
        #获取会话的历史会话
        history =  self.get_context_for_llm()

        if not history:
            return ""

        context_lines = []
        for msg in history:
            content_type = msg.get('content_type', '')
            if content_type == ContentType.THINKING:
                #context_lines.append(f"思考：{msg.get('content', '')}")
                continue
            elif content_type == ContentType.SYSTEM_MESSAGE:
                continue
            elif content_type == ContentType.TOOL_CALL:
                context_lines.append(f"工具调用：{msg.get('content', '')}")
                continue
            elif content_type == ContentType.TOOL_RESULT:
                context_lines.append(f"工具调用结果：{msg.get('content', '')}")
                continue
            elif content_type == ContentType.USER_INPUT:
                context_lines.append(f"用户输入：{msg.get('content', '')}")
                continue
            elif content_type == ContentType.ASSISTANT_RESPONSE:
                context_lines.append(f"助手回复：{msg.get('content', '')}")
                continue
        
        return "\n".join(context_lines)

    def _infer_content_type(self, role: str, content: str) -> ContentType:
        """推断内容类型"""
        if not isinstance(content, str):
            content = str(content)
        
        if role == "user":
            return ContentType.USER_INPUT
        elif role == "assistant":
            if content.startswith("Think:") or "reasoning" in content.lower():
                return ContentType.THINKING
            return ContentType.ASSISTANT_RESPONSE
        elif role == "tool":
            return ContentType.TOOL_RESULT
        elif role == "system":
            return ContentType.SYSTEM_MESSAGE
        return ContentType.ASSISTANT_RESPONSE

    def get_stats(self) -> Dict[str, Any]:
        """获取上下文统计信息"""
        return {
            "total_messages": len(self.messages),
            "total_tokens": self.token_usage,
            "max_tokens": self.max_tokens,
            "usage_ratio": self.token_usage / self.max_tokens,
            "compressed_messages": sum(1 for m in self.messages if m.is_compressed),
            "current_task_id": self.current_task_id
        }

    def set_current_task(self, task_id: str):
        """设置当前任务ID

        Args:
            task_id: 任务ID
        """
        self.current_task_id = task_id
        self.logger.debug(f"设置当前任务ID: {task_id}")

    def retrieve_relevant_history(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关历史记忆

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            相关历史记录
        """
        if not self.enable_long_term_memory:
            return []

        return self.long_term_memory.retrieve(query, top_k)

# 添加 compress_context 方法到 ContextManager 类
