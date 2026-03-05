import sqlite3
import json

conn = sqlite3.connect('data/assistant.db')
cursor = conn.cursor()

session_id = 'session_eb5b1f14'

print('=' * 80)
print(f'会话 {session_id} 数据完整性详细检查')
print('=' * 80)
print()

# 检查会话是否存在
cursor.execute('SELECT session_id, created_at FROM sessions WHERE session_id = ?', (session_id,))
session = cursor.fetchone()

if not session:
    print(f'❌ 未找到会话：{session_id}')
    conn.close()
    exit()

print('【会话信息】')
print(f'  会话 ID: {session[0]}')
print(f'  创建时间：{session[1]}')
print()

# 获取该会话的所有任务
cursor.execute('''
    SELECT task_id, task_type, status, user_input, result, plan, 
           current_step_idx, input_tokens, output_tokens, created_at, updated_at
    FROM tasks
    WHERE session_id = ?
    ORDER BY created_at DESC
''', (session_id,))

tasks = cursor.fetchall()

print(f'【任务信息】(共 {len(tasks)} 个任务)')
print()

if not tasks:
    print('  ⚠️ 该会话没有任务记录')
else:
    for task_idx, task in enumerate(tasks, 1):
        task_id, task_type, status, user_input, result, plan, current_step_idx, input_tokens, output_tokens, task_created, task_updated = task
        
        print(f'  任务 {task_idx}:')
        print(f'    任务 ID: {task_id}')
        print(f'    类型：{task_type}')
        print(f'    状态：{status} {"✅" if status == "completed" else ("⚠️" if status == "running" else "❌")}')
        print(f'    用户输入：{user_input}')
        print(f'    创建时间：{task_created}')
        print(f'    更新时间：{task_updated}')
        
        if result:
            result_preview = result[:150].replace('\n', ' ') if len(result) > 150 else result
            print(f'    结果：{result_preview}...')
        
        if input_tokens or output_tokens:
            print(f'    Token 使用：输入={input_tokens}, 输出={output_tokens}')
        
        # 获取该任务的步骤
        cursor.execute('''
            SELECT step_id, step_index, step_type, description, thought, result, 
                   skill_call, status, created_at
            FROM steps
            WHERE task_id = ?
            ORDER BY step_index
        ''', (task_id,))
        
        steps = cursor.fetchall()
        
        print(f'    步骤数量：{len(steps)} 个')
        
        if steps:
            print(f'    步骤详情:')
            for step_idx, step in enumerate(steps, 1):
                step_id, step_index, step_type, description, thought, result, skill_call, step_status, step_created = step
                print(f'      [{step_index}] {step_status} {"✅" if step_status == "completed" else ("⚠️" if step_status == "running" else "❌")}')
                if description:
                    desc_preview = description[:60].replace('\n', ' ')
                    print(f'          描述：{desc_preview}...')
                if thought:
                    thought_preview = thought[:60].replace('\n', ' ')
                    print(f'          思考：{thought_preview}...')
                if result:
                    result_preview = result[:60].replace('\n', ' ')
                    print(f'          结果：{result_preview}...')
                if skill_call:
                    try:
                        skill_data = json.loads(skill_call)
                        print(f'          技能：{skill_data.get("skill", "unknown")}')
                    except:
                        print(f'          技能调用：{skill_call[:40]}...')
        
        print()

# 数据完整性验证
print('【数据完整性验证】')
print()

# 1. 检查会话是否有任务
print(f'  1. 会话任务数：{len(tasks)} 个 {"✅" if len(tasks) > 0 else "❌"}')

# 2. 检查任务状态
completed_tasks = sum(1 for t in tasks if t[2] == 'completed')
running_tasks = sum(1 for t in tasks if t[2] == 'running')
print(f'  2. 任务状态分布：已完成={completed_tasks}, 进行中={running_tasks}, 总计={len(tasks)}')

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

# 6. 检查时间戳逻辑
print(f'  6. 时间戳逻辑:')
print(f'     - 会话创建：{session[1]}')
for task in tasks:
    print(f'     - 任务创建：{task[9]}, 更新：{task[10]}')

# 7. 检查孤立数据
cursor.execute('''
    SELECT COUNT(*) FROM tasks t
    LEFT JOIN sessions s ON t.session_id = s.session_id
    WHERE t.session_id = ? AND s.session_id IS NULL
''', (session_id,))
orphan_tasks = cursor.fetchone()[0]
print(f'  7. 孤立任务检查：{orphan_tasks} 个 {"✅" if orphan_tasks == 0 else "❌"}')

cursor.execute('''
    SELECT COUNT(*) FROM steps st
    LEFT JOIN tasks t ON st.task_id = t.task_id
    WHERE t.session_id = ? AND t.task_id IS NULL
''', (session_id,))
orphan_steps = cursor.fetchone()[0]
print(f'  8. 孤立步骤检查：{orphan_steps} 个 {"✅" if orphan_steps == 0 else "❌"}')

print()
print('=' * 80)
print('检查完成')
print('=' * 80)

conn.close()
