import pandas as pd

# 读取两个Excel文件
df1 = pd.read_excel(r'D:\resources\lingxi-assistant\员工信息表.xlsx')
df2 = pd.read_excel(r'D:\resources\lingxi-assistant\人员信息.xlsx')

# 按'姓名'字段进行左连接合并
merged = pd.merge(df1, df2, on='姓名', how='left')

# 保存合并后的数据到新文件
merged.to_excel(r'D:\resources\lingxi-assistant\合并后员工信息.xlsx', index=False)

print('合并成功！')
print(f'合并后行数: {len(merged)}')
print(f'合并后列名: {list(merged.columns)}')