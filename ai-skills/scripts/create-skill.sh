#!/usr/bin/env bash
set -euo pipefail

# Internal scaffold helper for `npm run new`.
# Public entrypoint: `npm run new <skill-name>`.

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "官方入口: npm run new <skill-name>" >&2
  echo "底层脚本用法: $0 <skill-name> [repo-root]" >&2
  echo "示例: npm run new image-audit" >&2
  echo "示例: $0 image-audit \$HOME/ai-skills" >&2
  exit 1
fi

SKILL_NAME="$1"
REPO_ROOT="${2:-$HOME/ai-skills}"
TEMPLATE_DIR="$REPO_ROOT/templates/skill-template"
TARGET_DIR="$REPO_ROOT/$SKILL_NAME"

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "未找到模板目录: $TEMPLATE_DIR" >&2
  exit 1
fi

if [ -e "$TARGET_DIR" ]; then
  echo "目标目录已存在: $TARGET_DIR" >&2
  exit 1
fi

cp -R "$TEMPLATE_DIR" "$TARGET_DIR"
find "$TARGET_DIR" -type f \( -name 'SKILL.md' -o -name 'README.md' -o -name 'openai.yaml' \) -print0 | \
  while IFS= read -r -d '' file; do
    perl -0pi -e 's/your-skill-name/'"$SKILL_NAME"'/g' "$file"
  done

echo "已创建 skill 模板: $TARGET_DIR"
echo "下一步:"
echo "  1. 编辑 $TARGET_DIR/SKILL.md 和 $TARGET_DIR/README.md"
echo "  2. 检查 $TARGET_DIR/agents/openai.yaml 中的 display_name、short_description、policy.allow_implicit_invocation"
echo "  3. 按需补充 references/、scripts/ 或 assets/"
echo "  4. 运行: npm run validate $SKILL_NAME"
echo "  5. 运行: npm run pack $SKILL_NAME"
echo "  6. 运行: npm run install $SKILL_NAME"
