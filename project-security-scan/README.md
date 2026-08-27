# 项目安全审计

面向 Node.js / TypeScript 仓库的只读安全审计 Skill，覆盖生产依赖、业务代码与交付配置，并输出可复核的 Markdown 报告。

## 适用场景

- 仓库、应用目录或 workspace 的发布前安全审计
- npm、Yarn、pnpm 依赖漏洞、生产可达性与维护兼容性核查
- 认证授权、输入校验、注入、XSS、SSRF、文件处理和供应链风险审计
- Dockerfile、CI/CD、部署配置和秘密暴露风险检查

不适用于仅审查 Git diff；这类任务应使用差异安全审查流程。

## 审计原则

- 默认只读，不修改源码、lockfile、依赖、配置或部署环境
- 不读取或输出密钥、token、cookie、`.env*` 内容和生产凭证
- 每条发现提供代码或依赖证据、生产归属、可达性、置信度与验证方式
- 工具、网络或私有依赖源导致的遗漏必须写入覆盖限制

## 使用示例

```text
使用 $project-security-scan 对这个 Node.js monorepo 做一次项目安全审计。
重点检查生产依赖、匿名接口的鉴权、跨租户资源访问和 Docker/CI 配置；只读审计，并在聊天中输出报告。
```

## 目录结构

```text
project-security-scan/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── references/
    └── checklist.md
```

目录 slug 保持为 `project-security-scan`，用户可见名称为“项目安全审计”。
`references/checklist.md` 由审计流程按项目技术栈按需读取，不替代主流程中的证据与可达性要求。

## 验证与打包

```bash
npm run validate project-security-scan
npm run pack project-security-scan
```
