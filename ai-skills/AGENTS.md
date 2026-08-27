# ai-skills — Codex Agent 工作指南

这个仓库是所有 skill 的唯一源码仓库，同时兼容 **OpenAI Codex CLI** 和 **Claude Code**。

## 仓库结构

```
ai-skills/
├── <skill-name>/           # skill 源码目录
│   ├── SKILL.md            # 必须，两平台共用（open agent skills standard）
│   ├── agents/
│   │   └── openai.yaml     # Codex UI 配置（display_name、brand_color 等）
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

`$base-guidelines` 是默认的全局编码基准；处理写代码、review、重构类任务时，优先遵循它。`$skill-builder` 仍用于指导 agent 按仓库规范补全跨平台 skill；它不再作为底层脚手架入口。

手动流程：

```bash
# 1. 初始化目录
npm run new <name>

# 2. 编写 SKILL.md、README.md

# 3. 按需补充 references/、scripts/、assets/

# 4. 验证
npm run validate <name>

# 5. 打包
npm run pack <name>

# 6. 安装到本地工具链
npm run install <name>
```

## SKILL.md 规范

```yaml
---
name: skill-name           # 小写字母 + 连字符，与目录名一致
description: 触发描述（影响隐式匹配，中英文均可）
---
```

- 500 行以内，细节放 `references/`
- 面向 AI agent 编写，不是面向人类
- 用祈使句，不说废话

## agents/openai.yaml 规范

```yaml
interface:
  display_name: "Skill 显示名"
  short_description: "一句短描述"
  brand_color: "#XXXXXX"     # 可选

policy:
  allow_implicit_invocation: true
```

## 命名规范

- 目录名：`小写字母-连字符`，如 `h5-compat-audit`

## 已有 Skill

| Skill | 触发方式 | 用途 |
|-------|----------|------|
| `base-guidelines` | `$base-guidelines` | 中文全局编码基准，约束最小变更、显式假设和验证闭环 |
| `learning-mentor` | `$learning-mentor` | 个性化学习方案 |
| `skill-builder` | `$skill-builder` | 补全跨平台 skill |
| `h5-compat-audit` | `$h5-compat-audit` | H5 兼容性审查 |

## 测试命令

```bash
# 查看已安装 skill
npm run list

# 打包验证
npm run validate <name>
```
