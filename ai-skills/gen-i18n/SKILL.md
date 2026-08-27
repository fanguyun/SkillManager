---
name: gen-i18n
description: 从 Excel 翻译表生成多语言 JSON 文件；适用于用户需要把含 Key 和语言列的 xlsx 表转换为 locale/translation JSON，或整理、修复、自动化 i18n 资源生成流程。
---

# Excel 多语言 JSON 生成

将 Excel 第一张工作表转换为按语言拆分的 JSON 文件。默认假设表格包含 `Key` 列，每个非排除列都是一种语言，输出文件名为 `<语言列名>.json`。

## 快速流程

1. 确认输入 Excel 路径、输出目录，以及是否需要自定义排除列。
2. 检查 Excel 表头：
   - 必须有 `Key` 列。
   - 默认排除 `Key`、`提出时间`、`Desc`。
   - 其余列会被当作语言列并生成 JSON。
3. 运行脚本：

```bash
node scripts/gen-i18n.js --excel ./origin.xlsx --output ./translation
```

4. 生成后检查输出目录中的 JSON 文件数量、语言名和关键 key 是否符合预期。

## 参数

- `--excel, -e <path>`：输入 Excel 文件，默认 `./origin.xlsx`。
- `--output, -o <dir>`：输出目录，默认 `./translation`。
- `--exclude, -x <cols>`：额外排除列，逗号分隔；会与默认排除列合并。
- `--empty-as, -m <value>`：单元格为空时写入的值，默认空字符串。
- `--keep-output, -k`：不清空已有输出目录；默认会先删除输出目录内的 `.json` 文件。
- `--help, -h`：显示帮助。

## 行为规则

- 只读取第一张工作表。
- 每行必须有非空 `Key` 才会写入。
- key 会转成字符串并去除首尾空白。
- 翻译值会转成字符串；空值使用 `--empty-as`。
- 默认只清理输出目录中的 `.json` 文件，不删除其他文件。
- 如果没有检测到语言列，停止并报告错误。

## 使用建议

- 输出目录应使用项目中的 locale 目录或临时目录，避免覆盖手工维护的 JSON。
- 如果语言列名包含空格、括号或区域码，生成文件名会保留原列名。
- 需要稳定文件名时，先在 Excel 中规范语言列名，例如 `en-US`、`zh-CN`、`ja-JP`。
- 大批量更新后，优先用 `git diff` 检查是否只有预期语言文件发生变化。

## 脚本

- 使用 `scripts/gen-i18n.js` 执行转换。
- 如果当前项目没有安装 `xlsx`，先在目标项目安装依赖，或在已有 `xlsx` 依赖的工具项目中运行。
