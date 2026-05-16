# -*- coding: utf-8 -*-
"""
代码推送配置文件
用法: 修改下方 COMMIT_MESSAGE 和 FILES 中的内容，然后运行 push_to_remote.py
"""

COMMIT_MESSAGE = """docs: 新增M6技术方案文档，更新M4/M6 spec文档和方案文档

本次更新内容：
1. 新增 M6技术方案.md（方案文档/M6技术方案.md）
   - 10章完整技术方案：模块定位/架构/数据模型/地理知识库/核心处理逻辑/输出格式/接口规范/依赖/测试/技术亮点
   - 含航迹分段、统计自适应骤变检测、城市途经、雷达名称映射、机场起降、中文时间格式等增强特性说明
   - 含多段式自然语言战报完整示例和全局态势摘要示例
2. 更新 M4技术方案.md（v2.0）
   - 模块定位从"静态全量展示版"演进为"带语义转化能力的多维态势交互看板"
   - 新增第7节：Flask服务器 + M6语义转化集成方案（API端点/双Tab页设计/技术实现/更新后布局图）
   - 交付标准从5项增到6项
3. 更新 项目总体说明文档.md
   - M4部分大幅扩展：技术架构/底图/传感器/业务/语义转化图层 + 启动方式
   - M6部分添加详细方案文档链接
4. 更新 M6 spec文档（spec/tasks/checklist）
   - spec.md 新增7个增强需求规格（航迹分段/骤变检测/城市途经/雷达名称/机场起降/中文时间/M4集成API）
   - tasks.md 新增任务9-15，更新依赖关系图
   - checklist.md 新增5个验收板块共32项，全部已勾选
5. 更新 M4 spec文档（spec/tasks/checklist）
   - spec.md 新增第7节Flask服务器+语义转化Tab集成方案
   - tasks.md 新增第二阶段任务7.1-7.5 + 更新依赖关系
   - checklist.md 新增Flask服务器验收/语义转化Tab/交互/样式/推送脚本共32项验收
"""

FILES = {
    "方案文档/M6技术方案.md": None,
    "方案文档/M4技术方案.md": None,
    "方案文档/项目总体说明文档.md": None,
    ".trae/specs/implement-m6-semantic-tool/spec.md": None,
    ".trae/specs/implement-m6-semantic-tool/tasks.md": None,
    ".trae/specs/implement-m6-semantic-tool/checklist.md": None,
    ".trae/specs/implement-m4-situation-visualization/spec.md": None,
    ".trae/specs/implement-m4-situation-visualization/tasks.md": None,
    ".trae/specs/implement-m4-situation-visualization/checklist.md": None,
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
