#!/usr/bin/env python3
"""Query route- and platform-specific ShortVideo configuration capabilities."""

from __future__ import annotations

import argparse
import json
import sys

from config_capabilities import (
    CapabilityCatalogError,
    PLATFORMS,
    TRACKS,
    format_capability_markdown,
    load_catalog,
    query_catalog,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", required=True, choices=TRACKS)
    parser.add_argument("--platform", required=True, choices=PLATFORMS)
    parser.add_argument("--version", help="Exact verified SDK/package version")
    parser.add_argument("--query", required=True, help="Field path, English token, or Chinese natural-language alias")
    parser.add_argument("--json", action="store_true", help="Print the resolved result or composite results as JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        catalog = load_catalog(args.track)
        matches = query_catalog(catalog, platform=args.platform, query=args.query, version=args.version)
    except CapabilityCatalogError as exc:
        print(f"feature config query failed: {exc}", file=sys.stderr)
        return 2
    if not matches:
        if args.version and args.version not in catalog["verifiedVersions"]:
            print(
                f"No verified behavior is recorded for `{args.track}` `{args.platform}` version `{args.version}`. "
                "Read the route API surface, keep the status unverified, and do not apply a version patch.",
                file=sys.stderr,
            )
        else:
            print(f"No configuration capability matched `{args.query}` in `{args.track}`.", file=sys.stderr)
        return 1
    mapped = [(score, capability) for score, capability in matches if capability.get("matchedMappings")]
    if mapped:
        best_mapped_score = mapped[0][0]
        best = [capability for score, capability in mapped if score >= best_mapped_score - 20]
    else:
        best_score = matches[0][0]
        best = [capability for score, capability in matches if score == best_score]
    if len(best) > 1 and not mapped:
        print("Query is ambiguous; refine it to one of:", file=sys.stderr)
        for capability in best:
            print(f"- {capability['id']}: {', '.join(capability['members'])}", file=sys.stderr)
        return 3
    if args.json:
        payload = {
            "track": catalog["track"],
            "platform": args.platform,
            "configurationSource": catalog["configurationSource"],
            "matches": best,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif len(best) > 1:
        print(f"# 组合配置查询：{args.query}")
        print()
        print(f"- 共命中 {len(best)} 个需要协同处理的配置组。")
        print("- 按下列中英文字段和值映射分别修改；不得只处理其中一处。")
        for capability in best:
            print()
            print(format_capability_markdown(catalog, capability, platform=args.platform))
    else:
        print(format_capability_markdown(catalog, best[0], platform=args.platform))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
