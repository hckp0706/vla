# -*- coding: utf-8 -*-
"""
代码推送配置文件
用法: 修改下方 COMMIT_MESSAGE 和 FILES 中的内容，然后运行 push_to_remote.py
"""

COMMIT_MESSAGE = """chore: 新增代码推送脚本

本次更新内容：
1. 新增 push_config.py: 推送配置文件，包含文件清单、commit message、远程仓库信息
2. 新增 push_to_remote.py: 推送脚本，支持同时推送到 GitHub 和 Gitee
   - 支持 --github / --gitee 参数单独推送
   - 支持 --dry-run 预览模式
   - 自动检测本地分支名并映射到远程分支
"""

FILES = {
    "m6_semantic_tool/__init__.py": None,
    "m6_semantic_tool/__main__.py": None,
    "m6_semantic_tool/converter.py": None,
    "m6_semantic_tool/feature_extractor.py": None,
    "m6_semantic_tool/flight_inferencer.py": None,
    "m6_semantic_tool/geo_data.py": None,
    "m6_semantic_tool/models.py": None,
    "m6_semantic_tool/narrative_generator.py": None,
    "m6_semantic_tool/requirements.txt": None,
    "tests/test_m6.py": None,
    "方案文档/项目总体说明文档.md": None,
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
