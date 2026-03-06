import sqlite3
import json

# 连接数据库
conn = sqlite3.connect('data/assistant.db')
cursor = conn.cursor()

# 查询会话信息
print('=== 会话信息 ===')
cursor.execute('SELECT * FROM sessions WHERE session_id = ?', ('session_b32f8398',))
session = cursor.fetchone()
if session:
    print(f'会话ID: {session[0]}')
    print(f'用户名: {session[1]}')
    print(f'创建时间: {session[2]}')
    print(f'更新时间: {session[3]}')
else:
    print('会话不存在')

print()

# 查询该会话的所有任务
print('=== 任务列表 ===')
cursor.execute('SELECT task_id, session_id, task_type, plan, user_input, result, status, current_step_idx, replan_count, error_info FROM tasks WHERE session_id = ? ORDER BY created_at DESC', ('session_b32f8398',))
tasks = cursor.fetchall()
print(f'找到 {len(tasks)} 个任务')
for i, task in enumerate(tasks, 1):
    print(f'\n--- 任务 {i} ---')
    print(f'任务ID: {task[0]}')
    print(f'会话ID: {task[1]}')
    print(f'任务类型: {task[2]}')
    print(f'计划: {task[3]}')
    print(f'用户输入: {task[4]}')
    print(f'结果: {task[5]}')
    print(f'状态: {task[6]}')
    print(f'当前步骤: {task[7]}')
    print(f'重计划次数: {task[8]}')
    print(f'错误信息: {task[9]}')
    
    # 查询该任务的所有步骤
    cursor.execute('SELECT step_id, task_id, step_index, step_type, description, thought, result, skill_call, status FROM steps WHERE task_id = ? ORDER BY step_index ASC', (task[0],))
    steps = cursor.fetchall()
    print(f'  步骤数量: {len(steps)}')
    for j, step in enumerate(steps, 1):
        print(f'  步骤 {j}:')
        print(f'    步骤ID: {step[0]}')
        print(f'    步骤索引: {step[2]}')
        print(f'    步骤类型: {step[3]}')
        print(f'    描述: {step[4]}')
        print(f'    思考: {step[5]}')
        print(f'    结果: {step[6]}')
        print(f'    技能调用: {step[7]}')
        print(f'    状态: {step[8]}')

conn.close()
