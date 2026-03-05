import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/assistant.db')
cursor = conn.cursor()

print('=' * 80)
print('数据库完整性检查报告')
print('=' * 80)
print(f'检查时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# 1. 总体统计
print('【总体统计】')
cursor.execute('SELECT COUNT(*) FROM sessions')
session_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM tasks')
task_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM steps')
step_count = cursor.fetchone()[0]

print(f'  会话总数：{session_count}')
print(f'  任务总数：{task_count}')
print(f'  步骤总数：{step_count}')
print()

# 2. 检查最新会话的完整数据
print('【最新会话详情】')
cursor.execute('''
    SELECT s.session_id, s.created_at, 
           COUNT(DISTINCT t.task_id) as task_count,
           COUNT(DISTINCT st.step_id) as step_count
    FROM sessions s
    LEFT JOIN tasks t ON s.session_id = t.session_id
    LEFT JOIN steps st ON t.task_id = st.task_id
    GROUP BY s.session_id, s.created_at
    ORDER BY s.created_at DESC
    LIMIT 3
''')

for idx, row in enumerate(cursor.fetchall(), 1):
    session_id, created_at, task_count, step_count = row
    print(f'\n会话 {idx}:')
    print(f'  会话 ID: {session_id}')
    print(f'  创建时间：{created_at}')
    print(f'  任务数量：{task_count}')
    print(f'  步骤数量：{step_count}')
    
    # 检查该会话的任务
    cursor.execute('''
        SELECT task_id, task_type, status, user_input, result, created_at
        FROM tasks 
        WHERE session_id = ?
        ORDER BY created_at DESC
    ''', (session_id,))
    
    tasks = cursor.fetchall()
    if tasks:
        print(f'\n  任务列表:')
        for task in tasks:
            task_id, task_type, status, user_input, result, task_created = task
            print(f'    ✓ 任务 ID: {task_id}')
            print(f'      类型：{task_type}')
            print(f'      状态：{status}')
            print(f'      输入：{user_input[:50] if user_input else "None"}...')
            print(f'      结果：{str(result)[:50] if result else "None"}...')
            
            # 检查该任务的步骤
            cursor.execute('''
                SELECT step_id, step_index, status, result
                FROM steps 
                WHERE task_id = ?
                ORDER BY step_index
            ''', (task_id,))
            
            steps = cursor.fetchall()
            if steps:
                print(f'      步骤 ({len(steps)}个):')
                for step in steps:
                    step_id, step_index, step_status, step_result = step
                    result_preview = str(step_result)[:40].replace('\n', ' ') if step_result else 'None'
                    print(f'        [{step_index}] {step_status}: {result_preview}...')
            else:
                print(f'      ⚠ 无步骤数据')
    else:
        print(f'  ⚠ 无任务数据')

# 3. 数据完整性验证
print('\n【数据完整性验证】')

# 检查孤立任务（没有会话的任务）
cursor.execute('''
    SELECT COUNT(*) FROM tasks t
    LEFT JOIN sessions s ON t.session_id = s.session_id
    WHERE s.session_id IS NULL
''')
orphan_tasks = cursor.fetchone()[0]
print(f'  孤立任务数：{orphan_tasks} {"✓" if orphan_tasks == 0 else "⚠"}')

# 检查孤立步骤（没有任务的步骤）
cursor.execute('''
    SELECT COUNT(*) FROM steps st
    LEFT JOIN tasks t ON st.task_id = t.task_id
    WHERE t.task_id IS NULL
''')
orphan_steps = cursor.fetchone()[0]
print(f'  孤立步骤数：{orphan_steps} {"✓" if orphan_steps == 0 else "⚠"}')

# 检查任务状态分布
cursor.execute('''
    SELECT status, COUNT(*) 
    FROM tasks 
    GROUP BY status
''')
print(f'\n  任务状态分布:')
for status, count in cursor.fetchall():
    print(f'    {status}: {count}')

# 检查步骤状态分布
cursor.execute('''
    SELECT status, COUNT(*) 
    FROM steps 
    GROUP BY status
''')
print(f'\n  步骤状态分布:')
for status, count in cursor.fetchall():
    print(f'    {status}: {count}')

print('\n' + '=' * 80)
print('检查完成')
print('=' * 80)

conn.close()
