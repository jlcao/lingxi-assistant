#!/usr/bin/env python3
"""向量存储层 - 基于 ChromaDB 的语义搜索"""

import logging
import os
from typing import List, Dict, Any, Optional
import hashlib

logger = logging.getLogger(__name__)

# 延迟导入大型依赖
CHROMADB_AVAILABLE = False
SENTENCE_TRANSFORMERS_AVAILABLE = False

# 仅在需要时导入
def _check_chromadb():
    global CHROMADB_AVAILABLE
    if not CHROMADB_AVAILABLE:
        try:
            import chromadb
            from chromadb.config import Settings
            CHROMADB_AVAILABLE = True
        except ImportError:
            CHROMADB_AVAILABLE = False
            logger.warning("ChromaDB 未安装，向量搜索功能不可用")
    return CHROMADB_AVAILABLE

def _check_sentence_transformers():
    global SENTENCE_TRANSFORMERS_AVAILABLE
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        try:
            from sentence_transformers import SentenceTransformer
            SENTENCE_TRANSFORMERS_AVAILABLE = True
        except ImportError:
            SENTENCE_TRANSFORMERS_AVAILABLE = False
            logger.warning("SentenceTransformers 未安装，向量搜索功能不可用")
    return SENTENCE_TRANSFORMERS_AVAILABLE


class VectorStore:
    """向量存储（基于 ChromaDB）"""
    
    def __init__(self, persist_directory: str = "./workspace/chroma_db"):
        """
        初始化向量存储
        
        Args:
            persist_directory: 持久化目录
        """
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.embedding_model = None
        
        if _check_chromadb():
            self._init_chromadb()
        
        if _check_sentence_transformers():
            self._init_embedding_model()
    
    def _init_chromadb(self):
        """初始化 ChromaDB"""
        try:
            # 导入 chromadb
            import chromadb
            from chromadb.config import Settings
            
            # 确保持久化目录存在
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # 创建客户端
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name="memories",
                metadata={"description": "Long-term memory storage"}
            )
            
            logger.info(f"ChromaDB 已初始化：{self.persist_directory}")
        except Exception as e:
            logger.error(f"初始化 ChromaDB 失败：{e}")
            self.client = None
            self.collection = None
    
    def _init_embedding_model(self):
        """初始化嵌入模型"""
        try:
            # 导入 SentenceTransformer
            from sentence_transformers import SentenceTransformer
            
            # 使用轻量级中文模型
            self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("SentenceTransformers 嵌入模型已加载")
        except Exception as e:
            logger.error(f"加载嵌入模型失败：{e}")
            self.embedding_model = None
    
    def _generate_id(self, content: str, category: str) -> str:
        """生成唯一 ID"""
        text = f"{content}:{category}"
        return hashlib.md5(text.encode()).hexdigest()
    
    def add_memory(self, memory_data: Dict[str, Any]) -> bool:
        """
        添加记忆到向量存储
        
        Args:
            memory_data: 记忆数据
        
        Returns:
            是否添加成功
        """
        if not self.collection or not self.embedding_model:
            logger.debug("向量存储未初始化，跳过添加")
            return False
        
        try:
            # 生成 ID
            memory_id = self._generate_id(
                memory_data['content'],
                memory_data['category']
            )
            
            # 生成嵌入
            embedding = self.embedding_model.encode(
                memory_data['content'],
                convert_to_numpy=True
            ).tolist()
            
            # 准备元数据
            metadata = {
                "category": memory_data['category'],
                "importance": memory_data['importance'],
                "workspace_path": memory_data.get('workspace_path', ''),
                "tags": ','.join(memory_data.get('tags', []))
            }
            
            # 添加到集合
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[memory_data['content']],
                metadatas=[metadata]
            )
            
            logger.debug(f"向量记忆已添加：{memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加向量记忆失败：{e}")
            return False
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        category: str = None,
        min_importance: int = 0,
        workspace_path: str = None
    ) -> List[Dict[str, Any]]:
        """
        向量语义搜索
        
        Args:
            query: 搜索查询
            n_results: 返回数量
            category: 分类过滤
            min_importance: 最小重要性
            workspace_path: 工作目录过滤
        
        Returns:
            搜索结果列表
        """
        if not self.collection or not self.embedding_model:
            logger.debug("向量存储未初始化，返回空结果")
            return []
        
        try:
            # 生成查询嵌入
            query_embedding = self.embedding_model.encode(
                query,
                convert_to_numpy=True
            ).tolist()
            
            # 构建 where 条件
            where_conditions = {}
            if category:
                where_conditions["category"] = category
            
            if workspace_path:
                where_conditions["workspace_path"] = workspace_path
            
            # 搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results * 2,  # 多取一些用于过滤
                where=where_conditions if where_conditions else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # 处理和过滤结果
            memories = []
            if results['ids'] and results['ids'][0]:
                for i, memory_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]
                    
                    # 过滤重要性
                    if metadata.get('importance', 0) < min_importance:
                        continue
                    
                    # 转换为记忆格式
                    memory = {
                        "id": memory_id,
                        "content": results['documents'][0][i],
                        "category": metadata.get('category', 'note'),
                        "tags": metadata.get('tags', '').split(',') if metadata.get('tags') else [],
                        "importance": metadata.get('importance', 3),
                        "workspace_path": metadata.get('workspace_path', ''),
                        "score": 1.0 / (1.0 + distance),  # 将距离转换为相似度分数
                        "distance": distance
                    }
                    memories.append(memory)
            
            logger.debug(f"向量搜索找到 {len(memories)} 条结果")
            return memories
            
        except Exception as e:
            logger.error(f"向量搜索失败：{e}")
            return []
    
    def delete_memory(self, content: str, category: str) -> bool:
        """删除记忆"""
        if not self.collection:
            return False
        
        try:
            memory_id = self._generate_id(content, category)
            self.collection.delete(ids=[memory_id])
            logger.debug(f"向量记忆已删除：{memory_id}")
            return True
        except Exception as e:
            logger.error(f"删除向量记忆失败：{e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.collection:
            return {"total": 0, "enabled": False}
        
        try:
            count = self.collection.count()
            return {
                "total": count,
                "enabled": True,
                "collection_name": self.collection.name
            }
        except Exception as e:
            logger.error(f"获取统计失败：{e}")
            return {"total": 0, "enabled": False}
    
    def is_available(self) -> bool:
        """检查向量搜索是否可用"""
        return self.collection is not None and self.embedding_model is not None
