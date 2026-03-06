import sqlite3

# 连接数据库
conn = sqlite3.connect('data/assistant.db')
cursor = conn.cursor()

# 模拟 get_session_info 方法
session_id = 'session_b32f8398'

# 查询会话信息
cursor.execute("""
    SELECT session_id, title, total_tokens, checkpoint_json, created_at, updated_at
    FROM sessions
    WHERE session_id = ?
""", (session_id,))
row = cursor.fetchone()

if row:
    session_id, title, total_tokens, checkpoint_json, created_at, updated_at = row
    
    print('=== 会话信息 ===')
    print(f'会话ID: {session_id}')
    print(f'标题: {title}')
    print(f'总token数: {total_tokens}')
    print(f'创建时间: {created_at}')
    print(f'更新时间: {updated_at}')
    print()
    
    # 获取该会话的所有任务
    cursor.execute("""
        SELECT task_id, task_type, plan, user_input, result, status, created_at, updated_at
        FROM tasks
        WHERE session_id = ?
        ORDER BY created_at ASC
    """, (session_id,))
    task_rows = cursor.fetchall()
    
    print(f'=== 任务列表 ({len(task_rows)} 个任务) ===')
    
    # 组装任务列表
    task_list = []
    for i, task_row in enumerate(task_rows, 1):
        task_id, task_type, plan, user_input, result, status, task_created_at, task_updated_at = task_row
        
        print(f'\n--- 任务 {i} ---')
        print(f'任务ID: {task_id}')
        print(f'任务类型: {task_type}')
        print(f'计划: {plan}')
        print(f'用户输入: {user_input}')
        print(f'结果: {result}')
        print(f'状态: {status}')
        
        # 查询该任务的所有步骤
        cursor.execute("""
            SELECT step_id, task_id, step_index, step_type, description, 
                   thought, result, skill_call, status, created_at
            FROM steps
            WHERE task_id = ?
            ORDER BY step_index ASC
        """, (task_id,))
        
        step_rows = cursor.fetchall()
        steps = []
        print(f'  步骤数量: {len(step_rows)}')
        
        for j, step_row in enumerate(step_rows, 1):
            step_dict = {
                "step_id": step_row[0],
                "task_id": step_row[1],
                "step_index": step_row[2],
                "step_type": step_row[3],
                "description": step_row[4],
                "thought": step_row[5],
                "result": step_row[6],
                "skill_call": step_row[7],
                "status": step_row[8],
                "created_at": step_row[9]
            }
            steps.append(step_dict)
            print(f'  步骤 {j}: {step_dict["description"][:50]}...')
        
        task_list.append({
            "task_id": task_id,
            "task_type": task_type,
            "plan": plan,
            "user_input": user_input,
            "result": result,
            "status": status,
            "created_at": task_created_at,
            "updated_at": task_updated_at,
            "steps": steps
        })
    
    print()
    print('=== 返回数据结构 ===')
    print({
        "session_id": session_id,
        "title": title,
        "task_count": len(task_list),
        "task_list": task_list,
        "total_tokens": total_tokens,
        "created_at": created_at,
        "updated_at": updated_at,
        "has_checkpoint": checkpoint_json is not None
    })

conn.close()
