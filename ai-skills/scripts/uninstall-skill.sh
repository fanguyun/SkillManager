#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "用法: $0 <skill-name>" >&2
  echo "示例: $0 h5-compat-audit" >&2
  exit 1
fi

SKILL_NAME="$1"
AGENTS_LINK="$HOME/.agents/skills/$SKILL_NAME"
CODEX_LINK="$HOME/.codex/skills/$SKILL_NAME"
CLAUDE_LINK="$HOME/.claude/skills/$SKILL_NAME"

remove_link() {
  local path="$1"
  if [ -L "$path" ]; then
    rm "$path"
    echo "已移除: $path"
  elif [ -e "$path" ]; then
    echo "跳过非软链接路径: $path" >&2
  else
    echo "不存在: $path"
  fi
}

remove_link "$CODEX_LINK"
remove_link "$CLAUDE_LINK"
remove_link "$AGENTS_LINK"
