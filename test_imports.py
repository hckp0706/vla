#!/usr/bin/env python3
"""
测试模块导入
"""

import sys
import os

print("Python version:", sys.version)
print("Current directory:", os.getcwd())

# 测试基本导入
try:
    import geographiclib
    print("✓ geographiclib imported successfully")
except Exception as e:
    print(f"✗ geographiclib import failed: {e}")

try:
    import numpy
    print("✓ numpy imported successfully")
except Exception as e:
    print(f"✗ numpy import failed: {e}")

# 测试项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from m1_trajectory_generator import models
    print("✓ models module imported successfully")
except Exception as e:
    print(f"✗ models module import failed: {e}")

try:
    from m1_trajectory_generator import knowledge_base
    print("✓ knowledge_base module imported successfully")
except Exception as e:
    print(f"✗ knowledge_base module import failed: {e}")

try:
    from m1_trajectory_generator import parser
    print("✓ parser module imported successfully")
except Exception as e:
    print(f"✗ parser module import failed: {e}")

try:
    from m1_trajectory_generator import trajectory_generator
    print("✓ trajectory_generator module imported successfully")
except Exception as e:
    print(f"✗ trajectory_generator module import failed: {e}")

try:
    from m1_trajectory_generator import app
    print("✓ app module imported successfully")
except Exception as e:
    print(f"✗ app module import failed: {e}")
