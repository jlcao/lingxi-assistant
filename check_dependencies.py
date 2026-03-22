#!/usr/bin/env python3
"""检查已安装的大型依赖包"""

import subprocess

# 要检查的大型依赖包
large_packages = [
    'chromadb',
    'sentence-transformers',
    'torch',
    'transformers',
    'scikit-learn',
    'numpy',
    'pandas'
]

print("检查已安装的大型依赖包...")
print("=" * 60)

# 获取所有已安装的包
result = subprocess.run(
    ['pip', 'list'],
    capture_output=True,
    text=True
)

installed_packages = result.stdout

for package in large_packages:
    if package in installed_packages:
        print(f"✅ {package} - 已安装")
    else:
        print(f"❌ {package} - 未安装")

print("=" * 60)
print("检查完成！")