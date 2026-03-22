from lingxi.core.session.database_manager import DatabaseManager
from lingxi.utils.config import GLOBAL_LINGXI_DIR

# 初始化数据库管理器
db = DatabaseManager()
print(f"数据库路径: {db.db_path}")
print(f"用户目录: {GLOBAL_LINGXI_DIR}")

# 查询会话数据
print('\n=== Sessions ===')
sessions = db.execute_sql('SELECT * FROM sessions WHERE session_id = ?', ('session_9b8686ee',), fetch=True)
print(sessions)

# 查询所有会话
print('\n=== All Sessions ===')
all_sessions = db.execute_sql('SELECT session_id, title, created_at FROM sessions', fetch=True)
print(all_sessions)

# 查询任务数据
print('\n=== Tasks ===')
tasks = db.execute_sql('SELECT * FROM tasks WHERE session_id = ?', ('session_9b8686ee',), fetch=True)
print(tasks)

# 如果有任务，查询步骤数据
if tasks:
    task_id = tasks[0][0]
    print('\n=== Steps ===')
    steps = db.execute_sql('SELECT * FROM steps WHERE task_id = ? ORDER BY step_index ASC', (task_id,), fetch=True)
    print(steps)
