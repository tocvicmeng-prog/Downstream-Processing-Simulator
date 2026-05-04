"""Substitute build-time placeholders in staged installer templates.

Replaces the following placeholders in every .bat / .txt / .md file under
installer/stage/:

    __DPSIM_VERSION__       → version field from pyproject.toml
    __DPSIM_RELEASE_DATE__  → today's date in YYYY-MM-DD (UTC)

Invoked by installer/build_installer.bat as a separate script (rather than
an inline ``python -c "..."``) because cmd.exe's ``^`` line-continuation
collides with our multi-line one-liner inside the .bat parser.

Run from the repo root:
    python installer\\substitute_version.py
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print("[substitute_version] ERROR: pyproject.toml not found "
              "(run from the repo root)")
        return 1

    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    if match is None:
        print("[substitute_version] ERROR: no version field in pyproject.toml")
        return 2

    version = match.group(1)
    release_date = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    placeholders = {
        "__DPSIM_VERSION__": version,
        "__DPSIM_RELEASE_DATE__": release_date,
    }
    stage = Path("installer/stage")
    if not stage.exists():
        print(f"[substitute_version] ERROR: {stage} does not exist")
        return 3

    n_files = 0
    n_subs = 0
    for path in stage.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (".bat", ".txt", ".md"):
            continue
        original = path.read_text(encoding="utf-8")
        replaced = original
        for placeholder, value in placeholders.items():
            replaced = replaced.replace(placeholder, value)
        if replaced != original:
            path.write_text(replaced, encoding="utf-8")
            n_files += 1
            for placeholder in placeholders:
                n_subs += original.count(placeholder)

    print(
        f"[substitute_version] Substituted version={version} "
        f"release_date={release_date} in {n_files} file(s); "
        f"{n_subs} replacement(s) total."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
