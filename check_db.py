import sqlite3

conn = sqlite3.connect('data/assistant.db')
cursor = conn.cursor()

# 查询最新的会话
cursor.execute("""
    SELECT session_id, created_at 
    FROM sessions 
    ORDER BY created_at DESC 
    LIMIT 5
""")

print('=== 最新会话 ===')
for row in cursor.fetchall():
    session_id = row[0]
    print(f'\n会话 ID: {session_id}')
    print(f'创建时间：{row[1]}')
    
    # 查询该会话的任务
    cursor.execute("""
        SELECT task_id, task_type, user_input, status, result, created_at
        FROM tasks 
        WHERE session_id = ?
    """, (session_id,))
    
    tasks = cursor.fetchall()
    if tasks:
        print(f'  任务数量：{len(tasks)}')
        for task in tasks:
            print(f'    - 任务 ID: {task[0]}')
            print(f'      类型：{task[1]}')
            print(f'      输入：{task[2][:50] if task[2] else "None"}...')
            print(f'      状态：{task[3]}')
            print(f'      结果：{(task[4][:50] + "...") if task[4] and len(task[4]) > 50 else task[4]}')
            print(f'      时间：{task[5]}')
            
            # 查询步骤
            cursor.execute("""
                SELECT step_index, step_type, status, description
                FROM steps
                WHERE task_id = ?
                ORDER BY step_index
            """, (task[0],))
            
            steps = cursor.fetchall()
            if steps:
                print(f'      步骤数量：{len(steps)}')
                for step in steps:
                    print(f'        {step[0]}. [{step[2]}] {step[1]}: {step[3][:50] if step[3] else "None"}...')
    else:
        print('  无任务数据')

conn.close()
