import logging
from typing import Dict

from lingxi.core.context.task_context import TaskContext
from lingxi.core.soul import SoulInjector
from lingxi.core.memory import MemoryManager, MemoryExtractor, UserMemoryManager
from lingxi.core.context.session_context import SessionContext
from lingxi.utils.config import get_workspace_path
from lingxi.core.memory import save_all_memories,save_memory_with_context,search_combined_memory

class ContextManager:
    """上下文管理器，负责管理会话上下文（单例模式）"""
    _instance = None
    
    def __new__(cls):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化上下文管理器"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.session_contexts: Dict[str, SessionContext] = {}
        self.logger = logging.getLogger(__name__)
        self.soul_injector = SoulInjector()
          # 记忆管理器
        self.user_memory_manager = UserMemoryManager()
        self._initialized = True
    
    def _build_soul_and_memory(self,context:TaskContext):
        self.soul_injector.reload()
         # 加载用户记忆
        count = self.user_memory_manager.load_all_memories()
        self.logger.info(f"加载了 {count} 条用户记忆")
        if self.soul_injector.soul_data:
            final_system_prompt = self.soul_injector.soul_content
            
            # 注入记忆到系统提示词
            context.soul_prompt=final_system_prompt
            # 将会话的系统提示词存储到上下文管理器
            self.logger.debug(f"SOUL 已注入到会话：{context.session_id}")
        
    def _build_memory_context(self,context:TaskContext) -> str:
        """构建记忆上下文"""
        # 实现记忆上下文构建逻辑
        memory_context = ''
        if hasattr(self.user_memory_manager, 'memory_manager') and hasattr(self.user_memory_manager.memory_manager, 'memories'):
            memories = self.user_memory_manager.memory_manager.memories.values()
            if memories:
                memory_items = []
                for memory in memories:
                    memory_items.append(f"- {memory.content} (分类: {memory.category})")
                memory_context = '\n'.join(memory_items)
                context.userMemory = memory_context
        return memory_context

    def get_session_context(self,session_id:str) -> SessionContext:
        """获取当前会话的上下文管理器"""
        session_context = self.session_contexts.get(session_id)
        if session_context is None:
            session_context = SessionContext(session_id)
            self.session_contexts[session_id] = session_context
            #self._build_soul_and_memory(session_id)
        return session_context
    
    def release_session_context(self,session_id:str):
        """释放会话上下文"""
        self.session_contexts.pop(session_id, None)
       
