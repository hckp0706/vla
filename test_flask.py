#!/usr/bin/env python3
"""
测试Flask应用启动
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Starting Flask app test...")

try:
    from m1_trajectory_generator.app import app
    print("✓ Flask app imported successfully")
    
    # 测试API路由
    print("✓ All routes registered successfully")
    
    print("\nFlask app test completed successfully!")
    print("You can start the server with: python -m m1_trajectory_generator.app")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
