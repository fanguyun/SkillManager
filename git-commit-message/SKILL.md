---
name: git-commit-message
description: "基于当前 Git 暂存区 diff 生成可直接使用的 Git CZ（Conventional Commits）提交内容。适用于用户要求查看 `git diff --cached`、拟定 commit message、编写规范提交说明或检查暂存改动是否适合一次提交；输出准确的 `type(scope): subject`，并在必要时补充正文和页脚。"
---

# Git 提交信息生成

只分析当前仓库的已暂存改动，生成与实际变更一致的 Git CZ 提交内容。默认使用 Conventional Commits 格式；保留 `feat`、`fix` 等标准英文类型和 `BREAKING CHANGE` 关键字，其余标题、列表项和页脚说明一律使用简体中文。

## 工作流程

1. 先检查项目根目录的提交规范配置，例如 `package.json` 中的 `config.commitizen`、`.czrc`、`.commitlintrc*`、`commitlint.config.*`；存在时遵循其类型、范围和格式约束。
2. 仅读取暂存区的改动内容：先执行 `git diff --cached --stat` 和 `git diff --cached --name-status`，再按需要执行 `git diff --cached --no-ext-diff`。
3. 如果暂存区为空，明确提示先执行 `git add <files>`，不要读取或依据未暂存 diff 猜测提交内容。
4. 从 diff 确认改动意图、影响范围和是否存在不兼容变更；不要根据文件名、分支名或用户描述虚构细节。
5. 未发现项目规范时，选择最准确的 Conventional Commits 类型：`feat`、`fix`、`docs`、`style`、`refactor`、`perf`、`test`、`build`、`ci`、`chore` 或 `revert`。
6. 范围明确且简短时使用 `(scope)`；范围不明确时省略。主题使用简体中文，写成简洁的动作结果，不加句号，避免超过 72 个字符。
7. 改动内容较多时，先输出中文标题，空一行后以 `- ` 开头的列表项描述每项重要变更；每项使用具体、简洁的中文动作描述。若只有一项简单改动，只输出标题。
8. 多个改动属于同一目标时使用一个主题和列表；若是互不相关的目标，先建议拆分暂存，再分别生成提交内容。
9. 暂存 diff 很大时，按暂存文件分段执行 `git diff --cached --no-ext-diff -- <path>`；二进制文件或无法确认语义的变更，应说明信息不足并请求补充，不要仅凭文件名生成提交内容。
10. 只有从 diff 能确认破坏兼容性时，添加 `BREAKING CHANGE: <中文兼容性说明>` 页脚；只有能确认关联编号时，添加 `Closes: #123` 等页脚。

## 输出格式

默认只输出一个可复制的 Markdown 代码块，不要包裹 `git commit -m` 命令：

```text
feat: 添加开放 API 用户路由和服务

- 新增用户登录、注册、获取当前用户信息和游戏角色列表的接口
- 实现请求限流机制，支持 Redis 限流
- 添加 OpenAPI 规范文档，包含接口描述和请求与响应格式
- 增加单元测试覆盖用户路由和服务逻辑

BREAKING CHANGE: 用户接口改为需要认证
```

仅主题足以描述改动时，省略空列表和页脚。用户明确要求命令时，再额外提供对应的 `git commit` 命令，并正确处理引号和多行内容。

## 边界

- 只读取项目的提交规范配置和 `git diff --cached` 或 `git diff --staged` 的改动内容；不要读取未暂存 diff、提交历史或远端信息来推断本次提交。
- 不执行 `git add`、`git commit`、`git reset`、`git restore` 或其他会改变仓库状态的命令。
- 不在提交信息中暴露 diff 中可能出现的密钥、令牌、个人信息或完整内部地址。
