import sqlite3
import json

conn = sqlite3.connect('data/assistant.db')
cursor = conn.cursor()

print('=' * 80)
print('最后一次任务数据完整性详细检查')
print('=' * 80)
print()

# 获取最新的任务
cursor.execute('''
    SELECT t.task_id, t.session_id, t.task_type, t.status, t.user_input, 
           t.result, t.plan, t.current_step_idx, t.created_at, t.updated_at
    FROM tasks t
    ORDER BY t.created_at DESC
    LIMIT 1
''')

task = cursor.fetchone()

if not task:
    print('❌ 没有找到任务记录')
    conn.close()
    exit()

task_id, session_id, task_type, status, user_input, result, plan, current_step_idx, created_at, updated_at = task

print('【会话信息】')
print(f'  会话 ID: {session_id}')
cursor.execute('SELECT created_at FROM sessions WHERE session_id = ?', (session_id,))
session_created = cursor.fetchone()[0]
print(f'  创建时间：{session_created}')
print()

print('【任务信息】')
print(f'  任务 ID: {task_id}')
print(f'  任务类型：{task_type}')
print(f'  任务状态：{status} {"✅" if status == "completed" else "⚠️"}')
print(f'  用户输入：{user_input}')
print(f'  创建时间：{created_at}')
print(f'  更新时间：{updated_at}')
print()

if result:
    print('【任务结果】')
    # 尝试解析 JSON
    try:
        result_data = json.loads(result) if result.startswith('{') else result
        if isinstance(result_data, str):
            # 如果是字符串，显示前 200 字符
            print(f'  {result[:200]}...')
        else:
            # 如果是字典，格式化显示
            print(f'  {json.dumps(result_data, indent=2, ensure_ascii=False)[:200]}...')
    except:
        print(f'  {result[:200]}...')
    print()

if plan:
    print('【任务计划】')
    try:
        plan_data = json.loads(plan)
        for idx, step in enumerate(plan_data, 1):
            print(f'  {idx}. {step}')
    except:
        print(f'  {plan[:200]}...')
    print()

# 获取该任务的所有步骤
cursor.execute('''
    SELECT step_id, step_index, step_type, description, thought, result, 
           skill_call, status, created_at
    FROM steps
    WHERE task_id = ?
    ORDER BY step_index
''', (task_id,))

steps = cursor.fetchall()

print(f'【步骤详情】(共 {len(steps)} 个步骤)')
print()

for idx, step in enumerate(steps, 1):
    step_id, step_index, step_type, description, thought, result, skill_call, status, step_created = step
    print(f'  步骤 {step_index}:')
    print(f'    Step ID: {step_id}')
    print(f'    状态：{status} {"✅" if status == "completed" else "⚠️"}')
    print(f'    类型：{step_type}')
    print(f'    描述：{description[:100] if description else "None"}...')
    
    if thought:
        print(f'    思考：{thought[:100]}...')
    
    if result:
        # 截断长结果
        result_preview = result[:100].replace('\n', ' ') if len(result) > 100 else result
        print(f'    结果：{result_preview}...')
    
    if skill_call:
        try:
            skill_data = json.loads(skill_call)
            print(f'    技能调用：{skill_data.get("skill", "unknown")}')
        except:
            print(f'    技能调用：{skill_call[:50]}...')
    
    print(f'    创建时间：{step_created}')
    print()

# 数据完整性验证
print('【数据完整性验证】')
print()

# 1. 检查步骤数量是否匹配
cursor.execute('SELECT COUNT(*) FROM steps WHERE task_id = ?', (task_id,))
step_count = cursor.fetchone()[0]
print(f'  1. 步骤数量检查：{step_count} 个步骤 {"✅" if step_count > 0 else "❌"}')

# 2. 检查所有步骤状态
cursor.execute('SELECT status, COUNT(*) FROM steps WHERE task_id = ? GROUP BY status', (task_id,))
step_statuses = cursor.fetchall()
print(f'  2. 步骤状态分布:')
for status, count in step_statuses:
    print(f'     - {status}: {count} 个')

# 3. 检查任务状态与步骤状态是否一致
all_steps_completed = all(status == 'completed' for _, _, _, _, _, _, _, status, _ in steps)
task_status_matches = (status == 'completed' and all_steps_completed) or (status == 'running' and not all_steps_completed)
print(f'  3. 任务状态与步骤状态一致性：{"✅" if task_status_matches else "⚠️"}')

# 4. 检查时间戳
print(f'  4. 时间戳检查:')
print(f'     - 会话创建：{session_created}')
print(f'     - 任务创建：{created_at}')
print(f'     - 任务更新：{updated_at}')
print(f'     - 最早步骤：{steps[0][8] if steps else "N/A"}')
print(f'     - 最晚步骤：{steps[-1][8] if steps else "N/A"}')

# 5. 检查数据关联
cursor.execute('SELECT COUNT(*) FROM tasks WHERE session_id = ?', (session_id,))
task_in_session = cursor.fetchone()[0]
print(f'  5. 任务关联会话：{"✅" if task_in_session > 0 else "❌"}')

cursor.execute('SELECT COUNT(*) FROM steps WHERE task_id = ?', (task_id,))
steps_in_task = cursor.fetchone()[0]
print(f'  6. 步骤关联任务：{"✅" if steps_in_task > 0 else "❌"}')

print()
print('=' * 80)
print('检查完成')
print('=' * 80)

conn.close()
