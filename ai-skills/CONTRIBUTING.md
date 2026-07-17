# Contributing

欢迎为这个仓库新增或改进 skills。

本仓库的目标是：

- 用一个统一源码仓库维护自研 skills
- 通过 `~/.agents/skills` 作为本机公共 skill 池
- 再由 Codex、Claude Code 等工具从公共池接入

## 基本原则

- 一个 skill 一个目录
- 技能源码只维护一份
- 优先复用模板和脚本，不手工重复搭目录
- skill 内容要面向“另一个 AI agent”编写，而不是面向人类终端用户
- 优先写可执行流程、检查清单和约束，不写空泛说明

## 目录规范

每个 skill 使用独立目录，推荐结构如下：

```text
<skill-name>/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
├── scripts/
└── assets/
```

说明：

- `SKILL.md`：必需，skill 主体
- `README.md`：建议提供，方便 GitHub 浏览和安装说明
- `agents/openai.yaml`：Codex/OpenAI 侧元数据，可选但推荐
- `references/`：按需加载的说明、规范、清单
- `scripts/`：可重复执行的自动化脚本
- `assets/`：模板、图标、示例文件等

不是所有 skill 都必须包含 `references/`、`scripts/`、`assets/`，按需添加即可。

## 命名规范

skill 目录名必须：

- 使用小写字母、数字、连字符
- 不使用空格
- 不使用下划线
- 尽量短且语义明确

推荐示例：

- `h5-compat-audit`
- `image-audit`
- `wechat-flow-check`

不推荐示例：

- `H5CompatAudit`
- `h5_compat_audit`
- `my new skill`

## SKILL.md 编写规范

`SKILL.md` 必须包含 YAML frontmatter：

```yaml
---
name: skill-name
description: 用一句话说明这个 skill 做什么、何时使用、主要产出什么。
---
```

正文建议包含：

- skill 目标和适用范围
- 快速流程
- 输出要求
- 需要时引用 `references/`

编写原则：

- 用祈使句或操作式表达
- 写清楚触发场景
- 写清楚默认假设
- 优先给“怎么做”
- 避免冗长背景介绍

## README.md 编写规范

每个 skill 的 `README.md` 建议包含：

- skill 的一句话介绍
- 目录结构
- 适用场景
- 安装方式
- 简单使用示例

README 主要给仓库访问者看，`SKILL.md` 主要给 agent 看。两者职责不同，不要完全混写。

## openai.yaml 规范

如需提供 `agents/openai.yaml`，建议至少包含：

```yaml
interface:
  display_name: "技能显示名"
  short_description: "一句短描述"
  default_prompt: "使用 $skill-name 完成对应任务。"
```

说明：

- 这部分主要服务 Codex/OpenAI 侧
- 不是所有工具都使用它
- 如果 skill 需要跨工具使用，也应保证仅靠 `SKILL.md` 仍然能工作

## references/ 规范

把以下内容放到 `references/`：

- 检查清单
- 兼容性矩阵
- 领域规则
- 配置说明
- 长篇参考资料

不要把所有细节都塞进 `SKILL.md`。优先让 `SKILL.md` 保持短小、可导航。

## scripts/ 规范

当某个动作需要重复执行，或希望降低 agent 每次重复生成代码的成本时，再放进 `scripts/`。

适合脚本化的内容：

- 代码扫描
- 内容生成
- 批量检查
- 格式转换
- 安装/卸载辅助操作

要求：

- 脚本应可重复执行
- 默认使用 ASCII
- 优先提供清晰的参数说明
- 添加后至少做一次本地验证

## 新增 skill 的推荐流程

### 1. 用模板创建

```bash
npm run new <skill-name>
```

### 2. 编辑 skill 内容

至少完成：

- `SKILL.md`
- `README.md`
- `agents/openai.yaml` 中的 `display_name`、`short_description`、`policy.allow_implicit_invocation`

按需补充：

- `references/`
- `scripts/`
- `assets/`

### 3. 安装到本地

```bash
npm run install <skill-name>
```

该脚本会把 skill 接入：

- `~/.agents/skills`
- `~/.codex/skills`
- `~/.claude/skills`

### 4. 检查当前安装状态

```bash
npm run list
```

### 5. 提交到 GitHub

```bash
cd <skills-repo>
git add .
git commit -m "feat: add <skill-name> skill"
git push
```

## 修改已有 skill 的建议

- 优先在源码目录 `<skills-repo>/<skill-name>` 中修改
- 不要直接改 `~/.agents/skills`、`~/.codex/skills`、`~/.claude/skills` 中的链接目标外壳
- 修改后，可用真实任务快速验证一次
- 如果新增了脚本，至少执行一次语法检查或最小实测

## 不建议提交的内容

不要提交：

- 本机缓存
- 临时测试文件
- 调试输出
- 与 skill 无关的个人配置
- 自动生成但无实际价值的文档堆积

## 提交信息建议

推荐使用 Conventional Commits：

- `feat: add h5-compat-audit skill`
- `feat: add skill template and install scripts`
- `fix: improve h5-compat-audit checklist`
- `docs: refine repository contribution guide`

## 提交前自检

提交前至少确认：

- 目录名符合命名规范
- `SKILL.md` frontmatter 正确
- README 和 skill 内容一致
- 脚本可以最小运行或通过语法检查
- 本地安装链路正常
- 不包含多余临时文件
