#!/usr/bin/env python3
# Static audit: find all "Назад" buttons and where they point.
#
# Usage:
#   python tools/back_nav_audit.py /path/to/project/root > back_nav_report.tsv
#
# Output columns:
#   file  line  button_text  callback_data  handler_hint

import re
import sys
from pathlib import Path

BACK_TEXT_RE = re.compile(r'InlineKeyboardButton\(\s*text\s*=\s*([\'"].*?[\'"])\s*,\s*callback_data\s*=\s*([\'"].*?[\'"])')
DECORATOR_EQ_RE = re.compile(r'@router\.callback_query\(\s*F\.data\s*==\s*([\'"].*?[\'"])\s*\)')
DECORATOR_SW_RE = re.compile(r'@router\.callback_query\(\s*F\.data\.startswith\(\s*([\'"].*?[\'"])\s*\)\s*\)')

def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] in "\"'" and s[-1] == s[0]:
        return s[1:-1]
    return s

def build_handler_index(app_dir: Path) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    for py in app_dir.rglob("*.py"):
        try:
            lines = py.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = py.read_text(encoding="utf-8", errors="replace").splitlines()

        for i, line in enumerate(lines, start=1):
            m1 = DECORATOR_EQ_RE.search(line)
            if m1:
                key = _strip_quotes(m1.group(1))
                idx.setdefault(key, []).append(f"{py}:{i}")
            m2 = DECORATOR_SW_RE.search(line)
            if m2:
                key = _strip_quotes(m2.group(1)) + "*"
                idx.setdefault(key, []).append(f"{py}:{i}")
    return idx

def find_handler_hint(cb: str, idx: dict[str, list[str]]) -> str:
    if cb in idx:
        return ",".join(idx[cb])
    for k, locs in idx.items():
        if k.endswith("*") and cb.startswith(k[:-1]):
            return ",".join(locs)
    return ""

def main():
    if len(sys.argv) < 2:
        print("Usage: back_nav_audit.py /path/to/project/root", file=sys.stderr)
        raise SystemExit(2)

    root = Path(sys.argv[1]).resolve()
    app_dir = root / "app"
    if not app_dir.exists():
        print("No app/ directory under:", root, file=sys.stderr)
        raise SystemExit(2)

    idx = build_handler_index(app_dir)

    for py in sorted(app_dir.rglob("*.py")):
        try:
            lines = py.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = py.read_text(encoding="utf-8", errors="replace").splitlines()

        for i, line in enumerate(lines, start=1):
            if "Назад" not in line and "🔙" not in line:
                continue
            m = BACK_TEXT_RE.search(line)
            if not m:
                continue
            btn_text = _strip_quotes(m.group(1))
            cb = _strip_quotes(m.group(2))
            hint = find_handler_hint(cb, idx)
            print(f"{py.relative_to(root)}\t{i}\t{btn_text}\t{cb}\t{hint}")

if __name__ == "__main__":
    main()
