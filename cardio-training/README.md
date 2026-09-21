# cardio-training

按心率区间与周训练量，给出可执行的有氧/心肺训练处方，并处理与力量训练的搭配。

## 目录

```text
cardio-training/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── heart-rate-zones.md
    └── weekly-templates.md
```

## 用途

- 估算心率区间（最大心率法、储备心率法），并用说话测试与 RPE 做体感校正
- 按 Zone 2 打底 + 少量高强度的结构排出周计划
- 处理有氧与力量训练同日的先后顺序、间隔与干扰
- 给出渐进规则、减量周判断与恢复信号

## 边界

不做诊断、不替代运动医学评估，也不承诺成绩或减重数字。

## 安装

把该目录链接到你的 skill 目录，例如：

```bash
ln -s /path/to/cardio-training ~/.agents/skills/cardio-training
```
