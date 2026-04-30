#!/usr/bin/env python3
"""Copy MP3 files from a source folder to a destination, prompting on duplicates."""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DUP_SUFFIX = re.compile(r"\s*[\(\[]\d+[\)\]]\s*$")
COPY_TAG = re.compile(r"\s*-?\s*copy(\s*\(\d+\))?\s*$", re.IGNORECASE)


def normalize(stem: str) -> str:
    s = stem.strip().lower()
    while True:
        new = COPY_TAG.sub("", s)
        new = DUP_SUFFIX.sub("", new)
        if new == s:
            break
        s = new
    return re.sub(r"\s+", " ", s).strip()


def fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def pick(group: list[Path]) -> Path | None:
    print(f"\nDuplicate group ({len(group)} files):")
    for i, p in enumerate(group, 1):
        st = p.stat()
        mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  [{i}] {p.name}")
        print(f"      {p.parent}  ({fmt_size(st.st_size)}, {mtime})")
    print("  [s] skip this group")
    while True:
        try:
            choice = input("Which to copy? ").strip().lower()
        except EOFError:
            return None
        if choice in ("s", "skip"):
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(group):
            return group[int(choice) - 1]
        print("Invalid choice, try again.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy mp3 files to a folder, asking which to keep when duplicates are found."
    )
    parser.add_argument(
        "--source", "-s", type=Path, default=Path.home() / "Downloads",
        help="source folder (default: ~/Downloads)",
    )
    parser.add_argument(
        "--dest", "-d", type=Path, required=True,
        help="destination folder (created if missing)",
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true",
        help="search source recursively",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="show what would be copied without copying",
    )
    args = parser.parse_args()

    if not args.source.is_dir():
        print(f"source folder not found: {args.source}", file=sys.stderr)
        return 1

    pattern = "**/*.mp3" if args.recursive else "*.mp3"
    files = sorted(p for p in args.source.glob(pattern) if p.is_file())
    if not files:
        print(f"no mp3 files found in {args.source}")
        return 0

    groups: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        groups[normalize(f.stem)].append(f)

    args.dest.mkdir(parents=True, exist_ok=True)
    copied = skipped = 0

    for group in groups.values():
        if len(group) == 1:
            chosen: Path | None = group[0]
        else:
            chosen = pick(group)
            if chosen is None:
                skipped += len(group)
                continue
            skipped += len(group) - 1

        target = args.dest / chosen.name
        if target.exists():
            print(f"already in dest, skipping: {target.name}")
            skipped += 1
            continue
        if args.dry_run:
            print(f"would copy: {chosen} -> {target}")
        else:
            shutil.copy2(chosen, target)
            print(f"copied: {chosen.name}")
        copied += 1

    print(f"\nDone. {copied} copied, {skipped} skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
