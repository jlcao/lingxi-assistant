#!/usr/bin/env python3
"""卸载大型依赖包"""

import subprocess

# 要卸载的大型依赖包
large_packages = [
    'chromadb',
    'sentence-transformers',
    'torch',
    'transformers',
    'scikit-learn',
    'numpy',
    'pandas'
]

print("开始卸载大型依赖包...")
print("=" * 60)

for package in large_packages:
    print(f"正在卸载: {package}...")
    result = subprocess.run(
        ['pip', 'uninstall', '-y', package],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"✅ {package} - 卸载成功")
    else:
        print(f"❌ {package} - 卸载失败")
        print(f"错误信息: {result.stderr}")

print("=" * 60)
print("卸载完成！")

# 验证卸载结果
print("\n验证卸载结果...")
result = subprocess.run(
    ['pip', 'list'],
    capture_output=True,
    text=True
)

installed_packages = result.stdout
print("=" * 60)

for package in large_packages:
    if package not in installed_packages:
        print(f"✅ {package} - 已成功卸载")
    else:
        print(f"❌ {package} - 仍然存在")

print("=" * 60)