"""Flutter capability-catalog validation."""

from __future__ import annotations

import json

from config_capabilities import CATALOG_ROOT, PLATFORMS, TRACKS, load_catalog, query_catalog

from .shared import assert_contains, fail, run, run_failure


def _matched_values(matches: list[tuple[int, dict]]) -> set[tuple[str, str]]:
    return {(item["member"], item["value"]) for _, cap in matches for item in cap.get("matchedMappings", {}).get("values", [])}


def validate_feature_capability_catalogs() -> None:
    if TRACKS != ("flutter",):
        fail("Flutter skill must expose exactly one capability track")
    schema = json.loads((CATALOG_ROOT / "schema.json").read_text(encoding="utf-8"))
    if schema["properties"]["schemaVersion"]["const"] != 2:
        fail("Capability schema must remain at version 2")
    if schema["properties"]["track"].get("const") != "flutter":
        fail("Flutter capability schema exposes a foreign track")
    if set(schema["properties"]["capabilities"]["items"]["properties"]["platforms"]["propertyNames"]["enum"]) != set(PLATFORMS):
        fail("Flutter capability schema platform boundary drifted")
    if {path.name for path in CATALOG_ROOT.glob("*.json")} != {"schema.json", "flutter.json"}:
        fail("Flutter skill contains a foreign capability catalog")

    catalog = load_catalog("flutter")
    if catalog["configurationSource"] != {"dart": "lib/meishe_feature_config.dart"}:
        fail("Flutter configuration source drifted")
    if (len(catalog["capabilities"]), len(catalog["fieldMappings"]), len(catalog["valueMappings"])) != (18, 72, 103):
        fail("Flutter capability data is incomplete")

    speed = query_catalog(catalog, platform="ios", version="2.0.2.1", query="隐藏拍摄页快慢速")
    if _matched_values(speed) != {("captureConfig.captureMenuItems", "speed")}:
        fail("Flutter speed menu mapping failed")
    requested = query_catalog(catalog, platform="android", version="2.0.2.1", query="去除拍摄倒计时合拍闪光灯编辑音效和配音")
    expected = {
        ("captureConfig.captureMenuItems", "timer"),
        ("captureConfig.dualMenuItems", "flashlight"),
        ("editConfig.editMenuItems", "audio"),
        ("editConfig.editMenuItems", "record"),
    }
    if not expected.issubset(_matched_values(requested)):
        fail("Flutter compound menu mapping is incomplete")
    if query_catalog(catalog, platform="ios", version="9.9.9", query="编辑菜单"):
        fail("Unknown versions must not inherit verified behavior")

    query_script = CATALOG_ROOT.parents[1] / "scripts" / "query_feature_config.py"
    output = run([
        str(query_script), "--track", "flutter", "--platform", "ios",
        "--version", "2.0.2.1", "--query", "隐藏拍摄页快慢速",
    ], "Flutter feature query")
    assert_contains(
        output,
        [
            "lib/meishe_feature_config.dart",
            "captureConfig.captureMenuItems",
            "speed",
            "建议修改：从 `captureConfig.captureMenuItems` 数组删除 `speed`",
            "Hot Restart",
        ],
        "Flutter query output",
    )
    run_failure([
        str(query_script), "--track", "react-native", "--platform", "ios", "--query", "拍摄菜单",
    ], "Flutter foreign-track rejection")
