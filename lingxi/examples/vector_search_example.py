#!/usr/bin/env python3
"""向量搜索使用示例"""

from lingxi.core.memory import MemoryManager


def main():
    print("=" * 60)
    print("向量搜索示例")
    print("=" * 60)
    
    # 初始化（启用向量搜索）
    config = {
        "workspace": {"default_path": "./workspace"},
        "memory": {
            "db_enabled": True,
            "vector_enabled": True,
            "vector_db_path": "./workspace/chroma_db"
        }
    }
    
    manager = MemoryManager(config)
    
    # 保存测试记忆
    print("\n1️⃣ 保存记忆...")
    test_memories = [
        ("我喜欢使用 Python 编程", "preference", ["coding", "python"], 4),
        ("JavaScript 也很流行", "preference", ["coding", "javascript"], 3),
        ("今天天气真好", "fact", [], 2),
        ("记得学习机器学习", "todo", ["study", "ml"], 4),
        ("项目下周上线", "fact", ["project"], 5),
    ]
    
    for content, category, tags, importance in test_memories:
        manager.save_memory(content, category, tags, importance)
        print(f"  ✓ {content}")
    
    # 关键词搜索
    print("\n2️⃣ 关键词搜索 '编程'...")
    results = manager.search_memory("编程", top_k=3, use_vector=False)
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.content} (关键词)")
    
    # 向量搜索
    print("\n3️⃣ 向量搜索 '写代码'...")
    results = manager.search_memory("写代码", top_k=3, use_vector=True)
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.content} (向量)")
    
    # 混合搜索
    print("\n4️⃣ 混合搜索 '学习新技能'...")
    results = manager.search_memory("学习新技能", top_k=3, use_vector=True, vector_weight=0.5)
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.content} (融合分数：{result.to_dict().get('fused_score', 0):.4f})")
    
    # 统计
    print("\n5️⃣ 统计信息...")
    stats = manager.get_memory_stats()
    print(f"  总记忆数：{stats['total']}")
    print(f"  按分类：{stats['by_category']}")


if __name__ == "__main__":
    main()
