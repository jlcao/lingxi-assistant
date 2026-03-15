#!/usr/bin/env python3
"""记忆功能使用示例"""

from lingxi.core.memory import MemoryManager, MemorySearch


def main():
    # 初始化记忆管理器
    manager = MemoryManager()
    
    # 保存记忆
    print("💾 保存记忆...")
    manager.save_memory(
        content="我喜欢使用 TypeScript",
        category="preference",
        tags=["coding", "language"],
        importance=4
    )
    
    manager.save_memory(
        content="当前项目是灵犀助手 v2.0",
        category="fact",
        tags=["project"],
        importance=5
    )
    
    manager.save_memory(
        content="记得实现向量搜索功能",
        category="todo",
        tags=["feature"],
        importance=3
    )
    
    # 搜索记忆
    print("\n🔍 搜索记忆...")
    search = MemorySearch(manager)
    results = search.search("TypeScript", top_k=5)
    
    for result in results:
        print(f"  - {result['category']}: {result['content']}")
    
    # 获取统计
    print("\n📊 记忆统计...")
    stats = manager.get_memory_stats()
    print(f"  总数：{stats['total']}")
    print(f"  按分类：{stats['by_category']}")
    
    # 保存到文件
    print("\n💾 保存到文件...")
    manager.save_to_file()
    print(f"  已保存到：{manager.memory_file}")


if __name__ == "__main__":
    main()
