# Git 提交信息生成

读取当前 Git 暂存区 diff，生成符合 Git CZ（Conventional Commits）的可复制提交内容。

## 适用场景

- 根据 `git diff --cached` 生成 commit message。
- 为已暂存的功能、修复、文档或重构改动选择正确的提交类型。
- 判断是否需要提交正文、关联 issue 页脚或 `BREAKING CHANGE`。

## 使用方式

在支持本地 Skill 的 agent 中调用：

```text
$git-commit-message
```

例如：

```text
读取已暂存的 Git diff，生成符合 git cz 规范的提交内容。
```

技能会先读取项目的提交规范配置，再读取已暂存变更；暂存区为空时会提示先执行 `git add <files>`，不会依据未暂存改动生成结果。

提交类型保留 Conventional Commits 的英文关键字；标题和变更列表使用简体中文。改动较多时，输出中文标题后空一行，再列出每项重要变更。

## 目录结构

```text
git-commit-message/
├── SKILL.md
├── README.md
└── agents/
    └── openai.yaml
```

## 安装

把该目录链接到你的 skill 目录，例如：

```bash
ln -s /path/to/git-commit-message ~/.agents/skills/git-commit-message
```
