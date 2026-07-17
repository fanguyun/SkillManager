#!/usr/bin/env bash
set -euo pipefail

is_skill_dir() {
  local path="$1"
  [ -e "$path/SKILL.md" ] || [ -e "$path/README.md" ]
}

is_skill_link() {
  local path="$1"
  [ -L "$path" ]
}

print_group() {
  local title="$1"
  local dir="$2"
  local mode="$3"

  echo "$title"
  if [ ! -d "$dir" ]; then
    echo "  (目录不存在: $dir)"
    return
  fi

  local found=0
  for path in "$dir"/*; do
    if [ ! -e "$path" ] && [ ! -L "$path" ]; then
      continue
    fi

    if [ "$mode" = "source" ]; then
      if ! is_skill_dir "$path"; then
        continue
      fi
    else
      if ! is_skill_link "$path" ] && [ ! -d "$path" ]; then
        continue
      fi
    fi

    found=1
    local name
    name="$(basename "$path")"
    if [ -L "$path" ]; then
      local target
      target="$(readlink "$path" 2>/dev/null || true)"
      echo "  - $name -> $target"
    else
      echo "  - $name"
    fi
  done

  if [ "$found" -eq 0 ]; then
    echo "  (空)"
  fi
}

print_group "源码目录" "$HOME/ai-skills" "source"
print_group "公共池" "$HOME/.agents/skills" "install"
print_group "Codex" "$HOME/.codex/skills" "install"
print_group "Claude" "$HOME/.claude/skills" "install"
