#!/usr/bin/env python3
"""Query Meishe ShortVideo skill documentation indexes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def default_index_path() -> Path:
    skill_root = Path(__file__).resolve().parents[1]
    return skill_root / "assets" / "shortvideo-docs" / "doc-map.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=default_index_path(), help="Path to doc-map.json")
    parser.add_argument(
        "--track",
        required=True,
        choices=["native"],
        help="Required integration track; cross-track queries are intentionally unsupported.",
    )
    parser.add_argument(
        "--platform",
        required=True,
        choices=["android"],
        help="Required target subplatform.",
    )
    parser.add_argument("--language", choices=["zh", "en"], help="Filter by document language")
    parser.add_argument("--tag", action="append", default=[], help="Require a tag. Can be passed multiple times.")
    parser.add_argument("--json", action="store_true", help="Print matching docs as JSON")
    return parser.parse_args()


def doc_matches(doc: dict[str, object], args: argparse.Namespace) -> bool:
    if doc.get("track") != args.track:
        return False
    if args.platform not in doc.get("platforms", []):
        return False
    if args.language and doc.get("language") != args.language:
        return False
    tags = set(doc.get("tags", []))
    if any(tag not in tags for tag in args.tag):
        return False
    return True


def platform_heading_range(doc: dict[str, object], platform: str) -> tuple[int, int | None, str] | None:
    expected = "ios" if platform == "ios" else "android"
    headings = doc.get("headings", [])
    if not isinstance(headings, list):
        return None
    for index, heading in enumerate(headings):
        if not isinstance(heading, dict):
            continue
        title = str(heading.get("title", "")).strip().lower()
        if title != expected:
            continue
        start = heading.get("line")
        level = heading.get("level")
        if not isinstance(start, int) or not isinstance(level, int):
            return None
        end: int | None = None
        for following in headings[index + 1 :]:
            if not isinstance(following, dict):
                continue
            following_line = following.get("line")
            following_level = following.get("level")
            if isinstance(following_line, int) and isinstance(following_level, int) and following_level <= level:
                end = following_line - 1
                break
        return start, end, str(heading.get("title", platform))
    return None


def main() -> int:
    args = parse_args()
    if not args.index.exists():
        raise SystemExit(f"Missing index: {args.index}")
    data = json.loads(args.index.read_text(encoding="utf-8"))
    docs = [doc for doc in data.get("docs", []) if doc_matches(doc, args)]
    if args.json:
        print(json.dumps(docs, ensure_ascii=False, indent=2))
        return 0

    route_key = args.track if args.track in {"flutter", "react-native"} else f"native-{args.platform}"
    route_group = data.get("route_groups", {}).get(route_key, {})
    references = route_group.get("references", {}) if isinstance(route_group, dict) else {}
    if isinstance(references, dict) and references:
        troubleshooting_key = (
            f"{args.platform}_troubleshooting"
            if args.track in {"flutter", "react-native"}
            else "troubleshooting"
        )
        selected_keys = ["route", "common", args.platform, troubleshooting_key, "package", "verified"]
        print("Selected route references:")
        for key in selected_keys:
            value = references.get(key)
            if value:
                print(f"  {key}: {value}")
        print()

    if not docs:
        print("No matching ShortVideo docs.")
        return 1
    for doc in docs:
        tags = ", ".join(doc.get("tags", []))
        platforms = ", ".join(doc.get("platforms", []))
        print(f"{doc['doc_id']}")
        print(f"  title: {doc['title']}")
        print(f"  track/platform/language: {doc['track']} / {platforms} / {doc['language']}")
        print(f"  asset: assets/shortvideo-docs/{doc['asset_path']}")
        platform_range = platform_heading_range(doc, args.platform)
        if platform_range:
            start, end, title = platform_range
            display_range = f"{start}-{end}" if end is not None else f"{start}-EOF"
            print(f"  selected platform section: {title}, lines {display_range}")
        print(f"  tags: {tags}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
