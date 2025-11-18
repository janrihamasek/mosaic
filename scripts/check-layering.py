#!/usr/bin/env python3
"""
Fail the build if services/controllers contain raw SQL/connection usage.
"""

import sys
from pathlib import Path


FORBIDDEN = [
    "conn.execute",
    "transactional_connection(",
    "sa_connection(",
    "db_transaction(",
    "with transactional_connection",
]

ALLOWLIST = {
    Path("backend/services/common.py"),
}


def scan_paths(paths):
    violations = []
    for path in paths:
        for file in Path(path).rglob("*.py"):
            if file in ALLOWLIST:
                continue
            text = file.read_text(encoding="utf-8")
            for idx, line in enumerate(text.splitlines(), start=1):
                lowered = line
                for token in FORBIDDEN:
                    if token in lowered:
                        violations.append(f"{file}:{idx}: {line.strip()}")
                        break
    return violations


def main() -> int:
    roots = [Path("backend/services"), Path("backend/controllers")]
    violations = scan_paths(roots)
    if violations:
        print("Forbidden data-layer usage found:")
        for v in violations:
            print(v)
        return 1
    print("Layering check passed: no forbidden tokens in services/controllers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
