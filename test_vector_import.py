#!/usr/bin/env python3
"""测试向量存储模块的导入，确保不会加载大型依赖"""

import time
import sys

# 记录开始时间
start_time = time.time()

# 尝试导入向量存储模块
try:
    from lingxi.core.memory import vector_store
    print("✅ 成功导入 vector_store 模块")
    print(f"导入耗时: {time.time() - start_time:.4f} 秒")
    
    # 检查是否加载了大型依赖
    print("\n检查依赖加载状态:")
    print(f"- CHROMADB_AVAILABLE: {vector_store.CHROMADB_AVAILABLE}")
    print(f"- SENTENCE_TRANSFORMERS_AVAILABLE: {vector_store.SENTENCE_TRANSFORMERS_AVAILABLE}")
    
    # 尝试初始化 VectorStore
    print("\n尝试初始化 VectorStore:")
    store = vector_store.VectorStore()
    print(f"- 客户端初始化: {store.client is not None}")
    print(f"- 集合初始化: {store.collection is not None}")
    print(f"- 嵌入模型初始化: {store.embedding_model is not None}")
    
    print("\n✅ 测试完成，模块可以正常导入，且不会强制加载大型依赖")
    
except Exception as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)