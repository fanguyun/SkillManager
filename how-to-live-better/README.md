# how-to-live-better

让 AI 助手照开源书《高性价比人生指南》回答具体的人生决策：该不该做、值不值、这笔钱要不要花、出事了第一步做什么、被裁了能领哪笔钱、这么干犯不犯法、该学什么手艺。

做的事情只有一件：**先把书里相关条目查出来，按书自己的算账方式排序，再答，每条注明出自第几节第几条**。查不到就说查不到，不凭记忆编数字。

## 目录

```text
how-to-live-better/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── lookup.md
    ├── safety.md
    └── provenance.md
```

## 用途

- 拿不准一件事划不划算，想知道花掉什么、换回什么、证据有多硬
- 出了具体状况（急症、被裁、被骗、装修押金被扣、工伤）想知道先做什么
- 想知道自己这种情况能领哪笔钱、办哪道手续
- 想把一笔开销（保险、体检套餐、保健品、培训课）判成该买还是智商税
- 想按自己的情况（怀孕、有老人、有孩子、35 岁、60 岁）挑出最值得做的几条

## 和上游自带 skill 的关系

书仓库里已经带了一个 `skills/life-decision-guide/`。这个 Skill 在它之上做了三处扩展：

| 扩展 | 解决什么 |
|---|---|
| **安全闸门前置**（第 0 步） | 急症、自杀念头、正在进行的法律程序、用药剂量，先给应急响应，不先讲性价比 |
| **敏感情形细则**（`references/safety.md`） | 给话术和纪律：不劝解、不追问方法、不提供剂量、四档受益人的风险面怎么写 |
| **来源与可信度**（`references/provenance.md`） | 许可与署名、证据分级怎么读、性价比档不等于证据等级、哪些局限必须主动说 |

流程仍沿用上游那套（定位节 → 捞条目 → 按 `index.html` 的算法排序 → 固定结构作答），因为那是这本书自己的算账方式。

**本 Skill 不复制任何条目原文**：书用 CC BY 4.0 发布，但条目随时在改（法条、金额、时限、名单都会动），存一份副本必然过期。所以只存读法和流程，条目一律现查。

## 用法

```
$how-to-live-better 朋友让我替他担保，签不签
$how-to-live-better 每天通勤两小时值不值
$how-to-live-better 被裁了，头两周先办哪几件事
$how-to-live-better 体检套餐里哪些可以直接不买
```

也可以不用 `$` 显式调用，问题里出现「划不划算」「该不该」「能领什么」「犯法吗」这类词会自动触发。

## 依赖

需要联网取正文，或本地已有书的仓库。首次使用会浅克隆约 2.3 MB：

```bash
git clone --depth 1 https://github.com/eternity4719/HowToLiveBetter.git "${TMPDIR:-/tmp}/hltb"
```

书仓库在本地（当前目录或上级目录有 `README.md` 和 `book/01-不要早死.md`）时直接读本地，不联网。

## 安装

把该目录链接到你的 skill 目录，例如：

```bash
ln -s /path/to/how-to-live-better ~/.agents/skills/how-to-live-better
```

或在仓库内执行：

```bash
npm run validate how-to-live-better
npm run pack how-to-live-better
npm run install how-to-live-better
```

## 署名

正文出自《高性价比人生指南》，作者 eternity4719，仓库 <https://github.com/eternity4719/HowToLiveBetter>，正文许可 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。本 Skill 只提供检索与作答规则，不复制正文内容。
