"""Native Android capability-catalog validation."""

from __future__ import annotations

import json

from config_capabilities import CATALOG_ROOT, PLATFORMS, TRACKS, load_catalog, query_catalog

from .shared import assert_contains, fail, run, run_failure


def _matched_values(matches: list[tuple[int, dict]]) -> set[tuple[str, str]]:
    return {(item["member"], item["value"]) for _, cap in matches for item in cap.get("matchedMappings", {}).get("values", [])}


def validate_feature_capability_catalogs() -> None:
    if TRACKS != ("native-android",):
        fail("Native Android skill must expose exactly one capability track")
    schema = json.loads((CATALOG_ROOT / "schema.json").read_text(encoding="utf-8"))
    if schema["properties"]["schemaVersion"]["const"] != 2:
        fail("Capability schema must remain at version 2")
    if schema["properties"]["track"].get("const") != "native-android":
        fail("Native Android capability schema exposes a foreign track")
    if schema["properties"]["capabilities"]["items"]["properties"]["platforms"]["propertyNames"].get("const") != "android":
        fail("Native Android capability schema platform boundary drifted")
    if PLATFORMS != ("android",):
        fail("Native Android query must expose only Android")
    if {path.name for path in CATALOG_ROOT.glob("*.json")} != {"schema.json", "native-android.json"}:
        fail("Native Android skill contains a foreign capability catalog")

    catalog = load_catalog("native-android")
    if catalog["configurationSource"] != {"java": "<applicationId path>/meishe/MeisheFeatureConfig.java"}:
        fail("Native Android configuration source drifted")
    if (len(catalog["capabilities"]), len(catalog["fieldMappings"]), len(catalog["valueMappings"])) != (23, 67, 101):
        fail("Native Android capability data is incomplete")
    integration_state = catalog["integrationVerifiedVersions"].get("2.0.2.1")
    if not integration_state or integration_state["status"] != "verified":
        fail("Native Android 2.0.2.1 integration evidence is missing")

    capture = query_catalog(catalog, platform="android", version="2.0.1.0", query="不显示拍摄的闪光灯和快慢速")
    if _matched_values(capture) != {
        ("captureMenuItems", "flashlight"),
        ("captureMenuItems", "speed"),
    }:
        fail("Native Android compound capture mapping failed")
    volume = query_catalog(catalog, platform="android", version="2.0.1.0", query="最大音量")
    if not volume or "0 < value <= 8" not in " ".join(volume[0][1]["constraints"]):
        fail("Native Android maxVolume boundary drifted")
    modes = query_catalog(catalog, platform="android", version="2.0.1.0", query="只保留9比16")
    if not modes or "禁止单元素" not in " ".join(modes[0][1]["constraints"]):
        fail("Native Android supportedEditModes boundary drifted")
    if query_catalog(catalog, platform="android", version="9.9.9", query="拍摄菜单"):
        fail("Unknown versions must not inherit verified behavior")

    query_script = CATALOG_ROOT.parents[1] / "scripts" / "query_feature_config.py"
    output = run([
        str(query_script), "--track", "native-android", "--platform", "android",
        "--version", "2.0.1.0", "--query", "不显示拍摄的闪光灯和快慢速",
    ], "Native Android feature query")
    assert_contains(
        output,
        [
            "MeisheFeatureConfig.java",
            "captureMenuItems",
            "flashlight",
            "speed",
            "建议修改：从 `captureMenuItems` 数组删除",
            "./gradlew :app:assembleDebug",
        ],
        "Native Android query output",
    )
    run_failure([
        str(query_script), "--track", "native-ios", "--platform", "ios", "--query", "拍摄菜单",
    ], "Native Android foreign-track rejection")
    layered_output = run_failure([
        str(query_script), "--track", "native-android", "--platform", "android",
        "--version", "2.0.2.1", "--query", "拍摄菜单",
    ], "Native Android integration/config version boundary")
    assert_contains(
        layered_output,
        [
            "has verified integration compatibility",
            "requested configuration behavior is not verified",
            "do not inherit a configuration patch",
        ],
        "Native Android layered version query",
    )
