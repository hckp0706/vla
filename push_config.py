# -*- coding: utf-8 -*-
"""
代码推送配置文件
用法: 修改下方 COMMIT_MESSAGE 和 FILES 中的内容，然后运行 push_to_remote.py
"""

COMMIT_MESSAGE = """feat(M4+M6): M4新增语义转化Tab页，支持M6自然语言战报交互生成

本次更新内容：
1. 新增 M4 Flask 服务器 (m4_situation_visualization/server.py)
   - 提供静态文件服务，支持浏览器直接访问M4前端
   - 暴露 /api/m6/convert 接口，将M2融合航迹转换为自然语言战报
   - 暴露 /api/m6/save 接口，手动保存语义转化结果
   - 自动将转化结果保存到 output/m6_semantic_tool/ 目录
2. M4前端新增「语义转化」Tab页
   - 在右侧控制面板新增Tab栏，支持「态势控制」和「语义转化」两页切换
   - 语义转化页：航迹下拉选择器，按track_id分组显示已加载的M2目标
   - 点击「执行语义转化」按钮，调用后端API生成自然语言战报
   - 实时显示态势战报概要和完整自然语言描述
   - 支持手动保存结果到文件
3. 新增 M6 输出目录 (output/m6_semantic_tool/)
   - 自动存储语义转化结果（JSON + TXT格式）
4. 样式优化
   - 控制面板宽度从280px增至300px
   - 新增Tab按钮、航迹选择器、战报显示区、状态提示等组件样式
"""

FILES = {
    "m4_situation_visualization/index.html": None,
    "m4_situation_visualization/css/style.css": None,
    "m4_situation_visualization/js/main.js": None,
    "m4_situation_visualization/server.py": None,
    "output/m6_semantic_tool/.gitkeep": None,
    "push_config.py": None,
    "push_to_remote.py": None,
}

GITHUB = {
    "owner": "hckp0706",
    "repo": "vla",
    "branch": "main",
}

GITEE = {
    "owner": "hsmm02",
    "repo": "vla",
    "branch": "master",
}
