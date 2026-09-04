# multi-mental-models

多元思维模型分析助手，用于针对一个问题进行多学科、多维度分析，并输出结构化判断、行动建议和风险提醒。

## 目录

```text
multi-mental-models/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    └── notes.md
```

## 用途

- 分析复杂问题、关键决策、产品方案、职业选择、学习规划、商业策略或组织问题。
- 从系统、经济、心理、社会、技术、组织、时间和伦理等维度筛选适用模型。
- 输出核心判断、问题重构、多维度分析、交叉结论和可执行建议。
- 同时兼容 OpenAI Codex CLI 的 `$multi-mental-models` 和 Claude Code 的 `/multi-mental-models`。

## 安装

把该目录链接到你的 skill 目录，例如：

```bash
ln -s /Users/fan/ai-skills/multi-mental-models ~/.agents/skills/multi-mental-models
```

也可以在仓库根目录运行：

```bash
npm run validate multi-mental-models
npm run pack multi-mental-models
npm run install multi-mental-models
```
