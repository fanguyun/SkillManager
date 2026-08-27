#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "用法: $0 <skill-name> [source-root]" >&2
  echo "示例: $0 h5-compat-audit \$HOME/ai-skills" >&2
  exit 1
fi

SKILL_NAME="$1"
SOURCE_ROOT="${2:-$HOME/ai-skills}"
SOURCE_DIR="$SOURCE_ROOT/$SKILL_NAME"
AGENTS_DIR="$HOME/.agents/skills"
CODEX_DIR="$HOME/.codex/skills"
CLAUDE_DIR="$HOME/.claude/skills"

if [ ! -d "$SOURCE_DIR" ]; then
  echo "未找到 skill 源码目录: $SOURCE_DIR" >&2
  exit 1
fi

mkdir -p "$AGENTS_DIR" "$CODEX_DIR" "$CLAUDE_DIR"
ln -sfn "$SOURCE_DIR" "$AGENTS_DIR/$SKILL_NAME"
ln -sfn ../../.agents/skills/"$SKILL_NAME" "$CODEX_DIR/$SKILL_NAME"
ln -sfn ../../.agents/skills/"$SKILL_NAME" "$CLAUDE_DIR/$SKILL_NAME"

echo "已安装 $SKILL_NAME"
echo "  源码:   $SOURCE_DIR"
echo "  公共池: $AGENTS_DIR/$SKILL_NAME"
echo "  Codex:  $CODEX_DIR/$SKILL_NAME"
echo "  Claude: $CLAUDE_DIR/$SKILL_NAME"
