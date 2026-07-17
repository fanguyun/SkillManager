# ai-skills — Claude Code 工作指南

这个仓库是所有 skill 的唯一源码仓库，同时兼容 **Claude Code** 和 **OpenAI Codex CLI**。

## 仓库结构

```
ai-skills/
├── <skill-name>/           # skill 源码目录
│   ├── SKILL.md            # 必须，两平台共用
│   ├── agents/
│   │   └── openai.yaml     # Codex UI 配置（推荐）
│   ├── references/         # 按需加载的参考文档
│   ├── scripts/            # 可执行脚本
│   └── assets/             # 模板、静态文件
├── <skill-name>.skill      # 打包产物，放根目录
└── scripts/                # 仓库管理脚本
```

## 创建新 Skill

官方入口：

```bash
npm run new <name>
```

`/base-guidelines` 是默认的全局编码基准；处理写代码、review、重构类任务时，优先遵循它。`/skill-builder` 仍用于指导 agent 按仓库规范补全跨平台 skill；它不再作为底层脚手架入口。

```bash
# 1. 初始化
npm run new <name>

# 2. 编写 SKILL.md、README.md（见下方规范）

# 3. 按需补充 references/、scripts/、assets/

# 4. 验证
npm run validate <name>

# 5. 打包（输出到仓库根目录）
npm run pack <name>

# 6. 安装到本地工具链
npm run install <name>
```

## SKILL.md 规范

```yaml
---
name: skill-name           # 小写字母 + 连字符
description: 一句话说明做什么、何时触发（中英文均可，影响隐式触发匹配）
---
```

- 500 行以内，细节放 `references/`
- 写给另一个 AI agent 看，不是给人看
- 用祈使句，不说废话

## agents/openai.yaml 规范

使用模板自带的 `agents/openai.yaml`，至少填写：
- `display_name`、`short_description`
- `policy.allow_implicit_invocation`（默认 true）

## 命名规范

- 目录名：`小写字母-连字符`，如 `h5-compat-audit`
- `.skill` 包名与目录名一致

## 已有 Skill

| Skill | 用途 |
|-------|------|
| `base-guidelines` | 中文全局编码基准，约束最小变更、显式假设和验证闭环 |
| `learning-mentor` | 个性化学习方案，学习策略专家角色 |
| `skill-builder` | 补全跨平台 skill 的工作流 |
| `h5-compat-audit` | H5 页面兼容性审查 |
