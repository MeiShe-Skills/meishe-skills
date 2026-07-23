"""React Native capability-catalog validation."""

from __future__ import annotations

import json

from config_capabilities import CATALOG_ROOT, PLATFORMS, TRACKS, load_catalog, query_catalog

from .shared import assert_contains, fail, run, run_failure


def _matched_fields(matches: list[tuple[int, dict]]) -> set[str]:
    return {item["member"] for _, cap in matches for item in cap.get("matchedMappings", {}).get("fields", [])}


def _matched_values(matches: list[tuple[int, dict]]) -> set[tuple[str, str]]:
    return {(item["member"], item["value"]) for _, cap in matches for item in cap.get("matchedMappings", {}).get("values", [])}


def validate_feature_capability_catalogs() -> None:
    if TRACKS != ("react-native",):
        fail("React Native skill must expose exactly one capability track")
    schema = json.loads((CATALOG_ROOT / "schema.json").read_text(encoding="utf-8"))
    if schema["properties"]["schemaVersion"]["const"] != 2:
        fail("Capability schema must remain at version 2")
    if schema["properties"]["track"].get("const") != "react-native":
        fail("React Native capability schema exposes a foreign track")
    if set(schema["properties"]["capabilities"]["items"]["properties"]["platforms"]["propertyNames"]["enum"]) != set(PLATFORMS):
        fail("React Native capability schema platform boundary drifted")
    if {path.name for path in CATALOG_ROOT.glob("*.json")} != {"schema.json", "react-native.json"}:
        fail("React Native skill contains a foreign capability catalog")

    catalog = load_catalog("react-native")
    if catalog["configurationSource"] != {
        "typescript": "src/meisheFeatureConfig.ts",
        "javascript": "src/meisheFeatureConfig.js",
    }:
        fail("React Native configuration source drifted")
    if (len(catalog["capabilities"]), len(catalog["fieldMappings"]), len(catalog["valueMappings"])) != (20, 72, 103):
        fail("React Native capability data is incomplete")

    speed = query_catalog(catalog, platform="android", version="2.0.2.1", query="隐藏拍摄页快慢速")
    if _matched_values(speed) != {("captureConfig.captureMenuItems", "speed")}:
        fail("React Native speed menu mapping failed")
    dual_timer = query_catalog(catalog, platform="ios", version="2.0.2.1", query="隐藏合拍倒计时")
    if _matched_values(dual_timer) != {("captureConfig.dualMenuItems", "timer")}:
        fail("React Native dual timer mapping leaked into capture")
    autocut = query_catalog(catalog, platform="android", version="2.0.2.1", query="关闭一键成片")
    if not {"albumConfig.useAutoCut", "templateConfig.useAutoCut"}.issubset(_matched_fields(autocut)):
        fail("React Native AutoCut flags are incomplete")
    if ("captureConfig.captureBottomMenuItems", "template") not in _matched_values(autocut):
        fail("React Native AutoCut template menu mapping is missing")
    auto_mic = query_catalog(catalog, platform="ios", version="2.0.2.1", query="拍摄自动静音")
    if not auto_mic or auto_mic[0][1]["platforms"]["ios"]["status"] != "partial":
        fail("React Native iOS auto-mic boundary drifted")
    if query_catalog(catalog, platform="android", version="9.9.9", query="拍摄菜单"):
        fail("Unknown versions must not inherit verified behavior")

    query_script = CATALOG_ROOT.parents[1] / "scripts" / "query_feature_config.py"
    output = run([
        str(query_script), "--track", "react-native", "--platform", "android",
        "--version", "2.0.2.1", "--query", "隐藏拍摄页快慢速",
    ], "React Native feature query")
    assert_contains(
        output,
        [
            "src/meisheFeatureConfig.ts",
            "captureConfig.captureMenuItems",
            "speed",
            "建议修改：从 `captureConfig.captureMenuItems` 数组删除 `speed`",
            "npm run android",
        ],
        "React Native query output",
    )
    run_failure([
        str(query_script), "--track", "flutter", "--platform", "android", "--query", "拍摄菜单",
    ], "React Native foreign-track rejection")
