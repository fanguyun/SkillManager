---
name: skill-builder
description: 补全同时兼容 Claude Code 和 OpenAI Codex CLI 的跨平台 skill。`npm run new` 负责初始化目录；skill-builder 负责指导 agent 完善 SKILL.md、README.md、agents/openai.yaml 与相关资源。当用户想补全新 skill、整理跨平台结构、或构建可复用工作流时触发。Use when polishing new skills that must work on both Claude Code (/skill-name) and OpenAI Codex CLI ($skill-name).
---

# Skill Builder — 跨平台 Skill 补全工作流

`npm run new <skill-name>` 是仓库里的官方脚手架入口。SKILL.md 是 Claude Code 和 Codex CLI 共用的格式（open agent skills standard）。本 skill 的职责是在脚手架生成后，指导 agent 按仓库规范补全 `SKILL.md`、`README.md`、`agents/openai.yaml`、references 和 scripts。

## 跨平台兼容说明

| 文件 | Claude Code | Codex CLI |
|------|-------------|-----------|
| `SKILL.md` | 必须，触发和指令 | 必须，触发和指令 |
| `agents/openai.yaml` | 不使用 | 可选，UI 配置 |
| 触发方式 | `/skill-name` 或隐式 | `$skill-name` 或隐式 |
| 打包 | `.skill` 文件 | `.skill` 文件 |

## 创建流程

### 第一步：初始化 skill 目录

```bash
npm run new <skill-name>
```

### 第二步：补全 SKILL.md 和 README.md

跨平台 SKILL.md 的注意点：
- `description` 要对两个平台的隐式触发都友好（中英文均可）
- 指令语言不依赖平台特定 API（如不要写 Claude 专有语法）
- 保持 500 行以内，细节放 references/

README.md 的注意点：
- 用一句话说明 skill 解决的问题
- 简要说明目录结构、适用场景和安装方式

### 第三步：检查 agents/openai.yaml（Codex 专用）

脚手架已生成 `agents/openai.yaml`，按需修改：

关键字段：
- `display_name`: 用户可见名称
- `short_description`: Codex UI 中展示的简短描述
- `allow_implicit_invocation`: 是否允许 Codex 自动选择此 skill（默认 true）
- `tools`: 如果 skill 需要 MCP 工具，在此声明依赖

### 第四步：补充或清理示例文件

删除模板中不需要的占位内容，只保留实际用到的资源。

### 第五步：验证和打包

```bash
npm run validate <skill-name>
npm run pack <skill-name>
```

输出 `.skill` 文件到仓库根目录。需要本地联调时，再执行：

```bash
npm run install <skill-name>
```

## Skill 目录最终结构

```
my-skill/
├── SKILL.md              # 两平台共用（必须）
├── agents/
│   └── openai.yaml       # Codex UI 配置（可选但推荐）
├── scripts/              # 可执行脚本（可选）
├── references/           # 参考文档（可选）
└── assets/               # 模板和静态文件（可选）
```

## agents/openai.yaml 模板

见 `assets/openai.yaml`。
