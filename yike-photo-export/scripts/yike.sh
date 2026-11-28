#!/usr/bin/env bash
# 一刻相册导出工具包装器：自动把工作区内的 Python 依赖加进 PYTHONPATH。
# 用法与 yike_export.py 完全一致，例如：
#   ./yike.sh check --browser chrome
#   ./yike.sh download --browser chrome --out ~/Pictures/yike --jobs 4
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
if [ -d "$REPO/.pydeps" ]; then
  export PYTHONPATH="$REPO/.pydeps${PYTHONPATH:+:$PYTHONPATH}"
fi
exec python3 "$HERE/yike_export.py" "$@"
