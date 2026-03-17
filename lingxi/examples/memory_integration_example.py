#!/usr/bin/env python3
"""记忆功能集成示例"""

from lingxi.core.memory import MemoryManager, MemoryExtractor


def main():
    print("=" * 60)
    print("记忆功能集成示例")
    print("=" * 60)
    
    # 初始化
    manager = MemoryManager()
    extractor = MemoryExtractor(manager)
    
    # 示例 1：从对话提取记忆
    print("\n1️⃣ 从对话提取记忆")
    print("-" * 60)
    
    session_history = [
        {"role": "user", "content": "我喜欢使用 TypeScript 而不是 JavaScript"},
        {"role": "assistant", "content": "好的，我记住了您的偏好"},
        {"role": "user", "content": "当前项目是灵犀助手 v2.0，这是一个智能助手项目"},
        {"role": "user", "content": "记得以后要实现向量搜索功能"},
        {"role": "user", "content": "我一定要记住这个重要的事情"},
    ]
    
    memories = extractor.extract_from_session(
        session_history,
        auto_save=True,
        min_importance=3
    )
    
    print(f"提取了 {len(memories)} 条记忆:")
    for memory in memories:
        print(f"  - [{memory.category}] {memory.content} (重要性：{'⭐' * memory.importance})")
    
    # 示例 2：搜索记忆
    print("\n2️⃣ 搜索记忆")
    print("-" * 60)
    
    from lingxi.core.memory import MemorySearch
    search = MemorySearch(manager)
    
    results = search.search("TypeScript", top_k=5)
    print(f"搜索 'TypeScript': 找到 {len(results)} 条")
    for result in results:
        print(f"  - {result['content']}")
    
    # 示例 3：获取统计
    print("\n3️⃣ 记忆统计")
    print("-" * 60)
    
    stats = manager.get_memory_stats()
    print(f"总记忆数：{stats['total']}")
    print(f"按分类：{stats['by_category']}")
    
    # 示例 4：保存到文件
    print("\n4️⃣ 保存到文件")
    print("-" * 60)
    
    manager.save_to_file()
    print(f"已保存到：{manager.memory_file}")
    
    # 显示文件内容
    import os
    if os.path.exists(manager.memory_file):
        print("\n文件内容预览:")
        with open(manager.memory_file, 'r') as f:
            content = f.read()
            print(content[:500] + "..." if len(content) > 500 else content)


if __name__ == "__main__":
    main()
