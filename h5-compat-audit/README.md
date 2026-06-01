# h5-compat-audit

一个面向 H5 页面和前端代码库的兼容性检查 skill，重点覆盖：

- Android 6+ 设备与老 WebView
- iPhone 7 之前机型对应的 Safari/WebKit 能力下限
- 微信内浏览器（iOS WKWebView / Android X5 或 WebView）
- 现代桌面端 Chrome、Safari、Edge
- 不考虑 IE

适合用于：

- 审查移动端 H5 页面是否会在旧设备上白屏、错位或交互异常
- 审查前端代码是否依赖高风险 JS / CSS / 浏览器 API
- 给出兼容性降级方案、修复建议和测试清单
- 检查微信内浏览器中的分享、OAuth、跳转、上传和滚动问题

## 适用场景

这个 skill 适合以下任务：

- 审查一个落地页、活动页或移动端 Web App 的兼容性风险
- 审查前端仓库中不适合旧安卓 WebView 或老 iPhone Safari 的实现
- 输出按优先级排序的问题清单和最小修复方案
- 在发版前补一个面向 Android / iPhone / 微信 / 桌面端的回归测试建议

## 输出特点

这个 skill 的默认输出目标是：

- 按 `P0` 到 `P3` 给问题分级
- 区分“已确认问题”和“高概率风险”
- 每条问题都写清影响平台、失败原因和最小修复方案
- 结尾补回归测试建议

## 目录结构

```text
h5-compat-audit/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── checklist.md
    └── targets.md
```

说明：

- `SKILL.md` 是 skill 主体
- `references/targets.md` 定义目标设备与浏览器基线
- `references/checklist.md` 提供审查清单和常见降级建议
- `agents/openai.yaml` 是面向 Codex / OpenAI 侧的元数据

## 安装

### 方式一：安装到公共池

如果你维护一个统一的 skills 仓库，可以先把本目录放入你的源码仓库，再链接到公共池：

```bash
ln -s /path/to/h5-compat-audit ~/.agents/skills/h5-compat-audit
```

再由不同工具从公共池接入：

```bash
ln -s ~/.agents/skills/h5-compat-audit ~/.codex/skills/h5-compat-audit
ln -s ~/.agents/skills/h5-compat-audit ~/.claude/skills/h5-compat-audit
```

### 方式二：直接安装到工具目录

如果你不维护公共池，也可以直接链接到工具目录：

```bash
ln -s /path/to/h5-compat-audit ~/.codex/skills/h5-compat-audit
ln -s /path/to/h5-compat-audit ~/.claude/skills/h5-compat-audit
```

## 兼容性说明

### Codex

- 可直接使用 `SKILL.md`
- `agents/openai.yaml` 可用于补充显示名、短描述和默认 prompt

### Claude Code

- 主要依赖 `SKILL.md`
- 通常不要求 `agents/openai.yaml`
- 同一个 skill 主体目录通常可以复用

## 使用示例

### 示例 1：审查页面

```text
使用 $h5-compat-audit 审查这个 H5 页面在安卓 6+、老 iPhone、微信内浏览器和桌面端的兼容性风险，并给出修复建议。
```

### 示例 2：审查代码库

```text
使用 $h5-compat-audit 检查这个前端项目里不适合旧安卓 WebView 和老 iPhone Safari 的 JS、CSS 和浏览器 API，并按 P0-P3 输出。
```

### 示例 3：发版前检查

```text
使用 $h5-compat-audit 对这个活动页做一次发版前兼容性审查，重点关注微信内浏览器、滚动行为、fixed 按钮、视频播放和上传流程。
```

## 适合检查的问题类型

- 可选链、空值合并、`Promise.finally` 等语法或 API 风险
- flex `gap`、`position: sticky`、`100vh`、`backdrop-filter` 等 CSS 风险
- fixed 底栏、软键盘遮挡、嵌套滚动、触摸交互问题
- 视频自动播放、canvas 内存压力、图片过大、文件上传问题
- 微信 JS-SDK、分享、OAuth、支付、跳转和 history 相关问题
- 弱设备上的性能瓶颈

## 发布建议

如果你要分享这个 skill：

- 保持目录名为 `h5-compat-audit`
- 如果发布到支持 zip 上传的平台，打包时让 zip 根目录包含 `h5-compat-audit/` 文件夹本身
- 如果发布到 GitHub，可以直接把本目录作为仓库根目录，或放进一个 skills 集合仓库中
