"""Native iOS capability-catalog validation."""

from __future__ import annotations

import json

from config_capabilities import CATALOG_ROOT, PLATFORMS, TRACKS, load_catalog, query_catalog

from .shared import assert_contains, fail, run, run_failure


def _matched_values(matches: list[tuple[int, dict]]) -> set[tuple[str, str]]:
    return {(item["member"], item["value"]) for _, cap in matches for item in cap.get("matchedMappings", {}).get("values", [])}


def validate_feature_capability_catalogs() -> None:
    if TRACKS != ("native-ios",):
        fail("Native iOS skill must expose exactly one capability track")
    schema = json.loads((CATALOG_ROOT / "schema.json").read_text(encoding="utf-8"))
    if schema["properties"]["schemaVersion"]["const"] != 2:
        fail("Capability schema must remain at version 2")
    if schema["properties"]["track"].get("const") != "native-ios":
        fail("Native iOS capability schema exposes a foreign track")
    if schema["properties"]["capabilities"]["items"]["properties"]["platforms"]["propertyNames"].get("const") != "ios":
        fail("Native iOS capability schema platform boundary drifted")
    if PLATFORMS != ("ios",):
        fail("Native iOS query must expose only iOS")
    if {path.name for path in CATALOG_ROOT.glob("*.json")} != {"schema.json", "native-ios.json"}:
        fail("Native iOS skill contains a foreign capability catalog")

    catalog = load_catalog("native-ios")
    if catalog["configurationSource"] != {"swift": "MeisheShortVideo/MeisheFeatureConfig.swift"}:
        fail("Native iOS configuration source drifted")
    if (len(catalog["capabilities"]), len(catalog["fieldMappings"]), len(catalog["valueMappings"])) != (22, 75, 100):
        fail("Native iOS capability data is incomplete")

    edit = query_catalog(catalog, platform="ios", version="2.0.2.1", query="不显示编辑的文字和编辑")
    if _matched_values(edit) != {
        ("editConfig.editMenuItems", "edit"),
        ("editConfig.editMenuItems", "text"),
    }:
        fail("Native iOS compound edit mapping failed")
    unsupported = query_catalog(catalog, platform="ios", version="2.0.2.1", query="禁用时间特效")
    if not unsupported or unsupported[0][1]["platforms"]["ios"]["status"] != "unsupported":
        fail("Native iOS unsupported field boundary drifted")
    if query_catalog(catalog, platform="ios", version="9.9.9", query="编辑菜单"):
        fail("Unknown versions must not inherit verified behavior")

    query_script = CATALOG_ROOT.parents[1] / "scripts" / "query_feature_config.py"
    output = run([
        str(query_script), "--track", "native-ios", "--platform", "ios",
        "--version", "2.0.2.1", "--query", "不显示编辑的文字和编辑",
    ], "Native iOS feature query")
    assert_contains(
        output,
        [
            "MeisheFeatureConfig.swift",
            "editConfig.editMenuItems",
            "text",
            "建议修改：从 `editConfig.editMenuItems` 数组删除",
            "Product > Run",
        ],
        "Native iOS query output",
    )
    unsupported_output = run([
        str(query_script), "--track", "native-ios", "--platform", "ios",
        "--version", "2.0.2.1", "--query", "禁用时间特效",
    ], "Native iOS unsupported feature query")
    assert_contains(
        unsupported_output,
        ["不要修改", "是否允许按当前版本自动修改：`false`"],
        "Native iOS unsupported mutation guard",
    )
    run_failure([
        str(query_script), "--track", "native-android", "--platform", "android", "--query", "拍摄菜单",
    ], "Native iOS foreign-track rejection")
