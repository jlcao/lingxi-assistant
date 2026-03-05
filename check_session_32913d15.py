import sqlite3
import json

conn = sqlite3.connect('data/assistant.db')
cursor = conn.cursor()

session_id = 'session_32913d15'

print('=' * 80)
print(f'会话 {session_id} 数据完整性检查')
print('=' * 80)
print()

# 检查会话
cursor.execute('SELECT session_id, user_name, title, created_at, updated_at FROM sessions WHERE session_id = ?', (session_id,))
session = cursor.fetchone()

if not session:
    print('❌ 未找到会话记录')
    conn.close()
    exit()

print('【会话信息】')
print(f'  会话 ID: {session[0]}')
print(f'  用户名：{session[1]}')
print(f'  标题：{session[2]}')
print(f'  创建时间：{session[3]}')
print(f'  更新时间：{session[4]}')
print()

# 检查任务
cursor.execute('''
    SELECT task_id, task_type, status, user_input, result, created_at, updated_at
    FROM tasks
    WHERE session_id = ?
    ORDER BY created_at DESC
''', (session_id,))

tasks = cursor.fetchall()

print(f'【任务信息】(共 {len(tasks)} 个任务)')
print()

for task_idx, task in enumerate(tasks, 1):
    task_id, task_type, status, user_input, result, task_created, task_updated = task
    
    print(f'  任务 {task_idx}:')
    print(f'    任务 ID: {task_id}')
    print(f'    类型：{task_type}')
    print(f'    状态：{status} {"✅" if status == "completed" else "⚠️"}')
    print(f'    用户输入：{user_input}')
    print(f'    创建时间：{task_created}')
    print(f'    更新时间：{task_updated}')
    
    if result:
        result_preview = result[:150].replace('\n', ' ') if len(result) > 150 else result
        print(f'    结果：{result_preview}...')
    
    # 检查该任务的步骤
    cursor.execute('''
        SELECT step_id, step_index, status, result, thought, created_at
        FROM steps
        WHERE task_id = ?
        ORDER BY step_index
    ''', (task_id,))
    
    steps = cursor.fetchall()
    
    print(f'    步骤数量：{len(steps)} 个')
    
    if steps:
        print(f'    步骤详情:')
        for step_idx, step in enumerate(steps, 1):
            step_id, step_index, step_status, step_result, thought, step_created = step
            print(f'      [{step_index}] {step_status} {"✅" if step_status == "completed" else "⚠️"}')
            if step_result:
                result_preview = step_result[:80].replace('\n', ' ')
                print(f'          结果：{result_preview}...')
            if thought:
                thought_preview = thought[:80].replace('\n', ' ')
                print(f'          思考：{thought_preview}...')
    
    print()

# 数据完整性验证
print('【数据完整性验证】')
print()

# 1. 检查会话是否有任务
print(f'  1. 会话任务数：{len(tasks)} 个 {"✅" if len(tasks) > 0 else "❌"}')

# 2. 检查任务状态
completed_tasks = sum(1 for t in tasks if t[2] == 'completed')
print(f'  2. 已完成任务：{completed_tasks}/{len(tasks)} 个')

# 3. 检查步骤总数
total_steps = sum(len(cursor.execute('SELECT * FROM steps WHERE task_id = ?', (t[0],)).fetchall()) for t in tasks)
print(f'  3. 总步骤数：{total_steps} 个')

# 4. 检查步骤状态
cursor.execute('''
    SELECT s.status, COUNT(*) 
    FROM steps s
    JOIN tasks t ON s.task_id = t.task_id
    WHERE t.session_id = ?
    GROUP BY s.status
''', (session_id,))
step_statuses = cursor.fetchall()
print(f'  4. 步骤状态分布:')
for status, count in step_statuses:
    print(f'     - {status}: {count} 个')

# 5. 检查数据关联
print(f'  5. 数据关联检查:')
for task in tasks:
    task_id = task[0]
    cursor.execute('SELECT COUNT(*) FROM steps WHERE task_id = ?', (task_id,))
    step_count = cursor.fetchone()[0]
    print(f'     - 任务 {task_id[-10:]}: {step_count} 个步骤 {"✅" if step_count > 0 else "❌"}')

# 6. 检查孤立数据
cursor.execute('''
    SELECT COUNT(*) FROM tasks t
    LEFT JOIN sessions s ON t.session_id = s.session_id
    WHERE t.session_id = ? AND s.session_id IS NULL
''', (session_id,))
orphan_tasks = cursor.fetchone()[0]
print(f'  6. 孤立任务检查：{orphan_tasks} 个 {"✅" if orphan_tasks == 0 else "❌"}')

cursor.execute('''
    SELECT COUNT(*) FROM steps st
    LEFT JOIN tasks t ON st.task_id = t.task_id
    WHERE t.session_id = ? AND t.task_id IS NULL
''', (session_id,))
orphan_steps = cursor.fetchone()[0]
print(f'  7. 孤立步骤检查：{orphan_steps} 个 {"✅" if orphan_steps == 0 else "❌"}')

print()
print('=' * 80)
print('检查完成')
print('=' * 80)

conn.close()
