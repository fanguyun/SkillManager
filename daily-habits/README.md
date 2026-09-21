# daily-habits

把「改善生活习惯」拆成可执行、可测量、可复盘的动作：睡眠作息、久坐打断、进食节律、烟酒、压力与体检节奏。

## 目录

```text
daily-habits/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── habit-protocols.md
    └── checkup-baseline.md
```

## 用途

- 找出真正值得先改的那一个瓶颈，而不是罗列所有问题
- 用「触发器 → 动作 → 最小可行版本」的方式设计习惯
- 规定睡眠、久坐、进食节律、烟酒的执行协议与常见失败原因
- 给出体检节奏、核心追踪指标与台账结构（配合 `xlsx`）

## 边界

不做诊断、不给用药建议、不承诺具体健康结果；异常指标一律建议就医确认。

## 安装

把该目录链接到你的 skill 目录，例如：

```bash
ln -s /path/to/daily-habits ~/.agents/skills/daily-habits
```
