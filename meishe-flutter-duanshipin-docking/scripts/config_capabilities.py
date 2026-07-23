"""Load and query route-isolated ShortVideo configuration capability catalogs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
CATALOG_ROOT = SKILL_ROOT / "references" / "config-capabilities"
TRACKS = ("flutter",)
PLATFORMS = ("android", "ios")
STATUSES = {
    "verified",
    "boundary_verified",
    "partial",
    "ineffective",
    "limited",
    "unsupported",
    "transport_verified",
    "unverified",
}
EVIDENCE_LEVELS = {
    "device-behavior",
    "media-output",
    "bridge-payload",
    "serialization",
    "static-api",
    "external-required",
}
ACTION_TERMS = (
    ("remove", "不显示"),
    ("remove", "隐藏"),
    ("remove", "删除"),
    ("remove", "移除"),
    ("remove", "去掉"),
    ("disable", "关闭"),
    ("disable", "禁用"),
    ("include", "重新显示"),
    ("include", "显示"),
    ("include", "保留"),
    ("include", "恢复"),
    ("enable", "开启"),
    ("enable", "启用"),
    ("enable", "打开"),
    ("set", "设置"),
    ("set", "修改"),
    ("set", "调整"),
    ("set", "改成"),
)


class CapabilityCatalogError(ValueError):
    pass


def catalog_path(track: str) -> Path:
    if track not in TRACKS:
        raise CapabilityCatalogError(f"Unknown track `{track}`; expected one of {', '.join(TRACKS)}")
    return CATALOG_ROOT / f"{track}.json"


def load_catalog(track: str) -> dict[str, Any]:
    path = catalog_path(track)
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapabilityCatalogError(f"Capability catalog is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CapabilityCatalogError(f"Capability catalog is invalid JSON: {path}: {exc}") from exc
    validate_catalog(catalog, expected_track=track)
    return catalog


def validate_catalog(catalog: dict[str, Any], *, expected_track: str | None = None) -> None:
    required_root = {
        "schemaVersion",
        "track",
        "configurationSource",
        "verifiedVersions",
        "fieldMappings",
        "valueMappings",
        "capabilities",
    }
    missing_root = required_root - set(catalog)
    if missing_root:
        raise CapabilityCatalogError(f"Catalog is missing root keys: {sorted(missing_root)}")
    if set(catalog) != required_root:
        raise CapabilityCatalogError(
            f"Catalog root keys do not match the route schema: {sorted(set(catalog) - required_root)}"
        )
    if catalog["schemaVersion"] != 2:
        raise CapabilityCatalogError("Catalog schemaVersion must be 2")
    track = catalog["track"]
    if track not in TRACKS or (expected_track and track != expected_track):
        raise CapabilityCatalogError(f"Catalog track mismatch: expected {expected_track}, got {track}")
    sources = catalog["configurationSource"]
    if not isinstance(sources, dict) or not sources or not all(isinstance(value, str) and value for value in sources.values()):
        raise CapabilityCatalogError(f"{track}: configurationSource must contain non-empty paths")
    versions = catalog["verifiedVersions"]
    if not isinstance(versions, list) or not versions or len(versions) != len(set(versions)):
        raise CapabilityCatalogError(f"{track}: verifiedVersions must be a non-empty unique list")
    capabilities = catalog["capabilities"]
    if not isinstance(capabilities, list) or not capabilities:
        raise CapabilityCatalogError(f"{track}: capabilities must be a non-empty list")

    seen_ids: set[str] = set()
    seen_members: set[str] = set()
    required_capability = {
        "id", "members", "aliases", "type", "default", "constraints", "enumValues",
        "dependencies", "conflicts", "mutationTarget", "platforms", "alternative", "verification",
    }
    allowed_platforms = {"android"} if track == "native-android" else {"ios"} if track == "native-ios" else set(PLATFORMS)
    for capability in capabilities:
        missing = required_capability - set(capability)
        if missing:
            raise CapabilityCatalogError(f"{track}: capability is missing keys: {sorted(missing)}")
        if set(capability) != required_capability:
            raise CapabilityCatalogError(
                f"{track}: capability keys do not match the route schema: "
                f"{sorted(set(capability) - required_capability)}"
            )
        capability_id = capability["id"]
        if not isinstance(capability_id, str) or not re.fullmatch(r"[a-z0-9.-]+", capability_id):
            raise CapabilityCatalogError(f"{track}: invalid capability id `{capability_id}`")
        if capability_id in seen_ids:
            raise CapabilityCatalogError(f"{track}: duplicate capability id `{capability_id}`")
        seen_ids.add(capability_id)
        members = capability["members"]
        aliases = capability["aliases"]
        if not isinstance(members, list) or not members or len(members) != len(set(members)):
            raise CapabilityCatalogError(f"{track}/{capability_id}: members must be a non-empty unique list")
        if not isinstance(aliases, list) or not aliases or len(aliases) != len(set(aliases)):
            raise CapabilityCatalogError(f"{track}/{capability_id}: aliases must be a non-empty unique list")
        duplicate_members = seen_members.intersection(members)
        if duplicate_members:
            raise CapabilityCatalogError(f"{track}: fields appear in multiple capabilities: {sorted(duplicate_members)}")
        seen_members.update(members)
        platforms = capability["platforms"]
        if not isinstance(platforms, dict) or set(platforms) != allowed_platforms:
            raise CapabilityCatalogError(
                f"{track}/{capability_id}: platforms must be exactly {sorted(allowed_platforms)}"
            )
        for platform, state in platforms.items():
            if set(state) != {"version", "status", "evidence", "behavior"}:
                raise CapabilityCatalogError(
                    f"{track}/{capability_id}/{platform}: state keys do not match the route schema"
                )
            if state.get("status") not in STATUSES:
                raise CapabilityCatalogError(f"{track}/{capability_id}/{platform}: invalid status")
            if state.get("evidence") not in EVIDENCE_LEVELS:
                raise CapabilityCatalogError(f"{track}/{capability_id}/{platform}: invalid evidence level")
            version = state.get("version")
            if version not in versions:
                raise CapabilityCatalogError(
                    f"{track}/{capability_id}/{platform}: version `{version}` is not declared as verified"
                )
            if not state.get("behavior"):
                raise CapabilityCatalogError(f"{track}/{capability_id}/{platform}: behavior is required")

    field_mappings = catalog["fieldMappings"]
    if not isinstance(field_mappings, dict) or set(field_mappings) != seen_members:
        missing = sorted(seen_members - set(field_mappings)) if isinstance(field_mappings, dict) else sorted(seen_members)
        extra = sorted(set(field_mappings) - seen_members) if isinstance(field_mappings, dict) else []
        raise CapabilityCatalogError(
            f"{track}: fieldMappings must cover every member exactly; missing={missing}, extra={extra}"
        )
    for member, mapping in field_mappings.items():
        _validate_bilingual_mapping(mapping, f"{track}/fieldMappings/{member}")

    value_mappings = catalog["valueMappings"]
    if not isinstance(value_mappings, dict):
        raise CapabilityCatalogError(f"{track}: valueMappings must be an object")
    for mapping_key, mapping in value_mappings.items():
        if not isinstance(mapping_key, str) or "::" not in mapping_key:
            raise CapabilityCatalogError(f"{track}: invalid value mapping key `{mapping_key}`")
        member, value = mapping_key.split("::", 1)
        if member not in seen_members or not value:
            raise CapabilityCatalogError(f"{track}: value mapping references unknown member `{mapping_key}`")
        _validate_bilingual_mapping(mapping, f"{track}/valueMappings/{mapping_key}")


def _validate_bilingual_mapping(mapping: Any, label: str) -> None:
    if not isinstance(mapping, dict) or set(mapping) != {"zh", "aliases"}:
        raise CapabilityCatalogError(f"{label}: mapping must contain only `zh` and `aliases`")
    zh = mapping["zh"]
    aliases = mapping["aliases"]
    if not isinstance(zh, str) or not zh.strip():
        raise CapabilityCatalogError(f"{label}: zh must be a non-empty string")
    if (
        not isinstance(aliases, list)
        or len(aliases) != len(set(aliases))
        or not all(isinstance(alias, str) and alias.strip() for alias in aliases)
    ):
        raise CapabilityCatalogError(f"{label}: aliases must be a unique string list")


def _normalize_search_text(value: str) -> str:
    normalized = value.strip().casefold().replace("的", "")
    return re.sub(r"[^0-9a-z_\u4e00-\u9fff]+", "", normalized)


def _term_score(needle: str, term: str) -> int:
    candidate = _normalize_search_text(term)
    if not candidate:
        return 0
    if needle == candidate:
        return 120
    if candidate in needle:
        return 90 + min(len(candidate), 20)
    if candidate.isascii() and needle in candidate:
        return 60
    return 0


def _detected_actions(query: str) -> list[dict[str, str]]:
    normalized = _normalize_search_text(query)
    matches: list[dict[str, str]] = []
    matched_terms: list[str] = []
    for action, term in ACTION_TERMS:
        normalized_term = _normalize_search_text(term)
        if normalized_term not in normalized:
            continue
        if any(normalized_term in previous for previous in matched_terms):
            continue
        matches.append({"action": action, "term": term})
        matched_terms.append(normalized_term)
    return matches


def _mapping_terms(identifier: str, mapping: dict[str, Any]) -> list[str]:
    terminal = identifier.rsplit(".", 1)[-1]
    return [identifier, terminal, mapping["zh"], *mapping["aliases"]]


def _apply_instructions(track: str, platform: str) -> list[str]:
    if track not in TRACKS:
        raise CapabilityCatalogError(f"Unsupported Flutter track `{track}`")
    device_id = "<ANDROID_DEVICE_ID>" if platform == "android" else "<IOS_DEVICE_ID>"
    return [
        f"flutter run -d {device_id}",
        "活动 flutter run 终端按大写 R 执行 Hot Restart",
    ]


def _suggested_mutation(
    catalog: dict[str, Any],
    capability: dict[str, Any],
    platform: str,
) -> dict[str, Any]:
    state = capability["platforms"][platform]
    matched = capability.get("matchedMappings", {})
    actions = matched.get("actions", [])
    fields = matched.get("fields", [])
    values = matched.get("values", [])
    action = actions[0]["action"] if actions else "inspect"
    member = values[0]["member"] if values else fields[0]["member"] if fields else capability["members"][0]
    value = values[0]["value"] if values else None
    blocked = state["status"] in {"ineffective", "unsupported", "unverified"}
    if blocked:
        instruction = (
            f"不要修改 `{member}` 来实现该需求；当前版本状态为 `{state['status']}`。"
            f"使用替代方案：{capability['alternative'] or '先确认 SDK 公开 API 并重新验证。'}"
        )
    elif action == "remove" and value is not None:
        instruction = f"从 `{member}` 数组删除 `{value}`，保持其余元素原顺序。"
    elif action == "include" and value is not None:
        instruction = f"在 `{member}` 数组中加入 `{value}`，避免重复元素。"
    elif action == "disable":
        instruction = f"将 `{member}` 设置为 `false`。"
    elif action == "enable":
        instruction = f"将 `{member}` 设置为 `true`。"
    elif action == "set" and value is not None:
        instruction = f"将 `{member}` 设置为 `{value}`。"
    else:
        instruction = f"在 `{capability['mutationTarget']}` 检查并修改 `{member}`。"
    return {
        "allowed": not blocked,
        "targetFiles": list(catalog["configurationSource"].values()),
        "member": member,
        "operation": action,
        "value": value,
        "instruction": instruction,
        "constraints": capability["constraints"],
        "applyCommands": _apply_instructions(catalog["track"], platform),
        "verification": capability["verification"],
    }


def query_catalog(
    catalog: dict[str, Any],
    *,
    platform: str,
    query: str,
    version: str | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    if platform not in PLATFORMS:
        raise CapabilityCatalogError(f"Unknown platform `{platform}`; expected android or ios")
    track = catalog["track"]
    allowed = {"android"} if track == "native-android" else {"ios"} if track == "native-ios" else set(PLATFORMS)
    if platform not in allowed:
        raise CapabilityCatalogError(f"Track `{track}` does not expose platform `{platform}`")
    if version and version not in catalog["verifiedVersions"]:
        return []

    needle = _normalize_search_text(query)
    if not needle:
        raise CapabilityCatalogError("Query must not be empty")
    actions = _detected_actions(query)
    mapping_needle = needle
    for action in actions:
        mapping_needle = mapping_needle.replace(_normalize_search_text(action["term"]), "")
    if not mapping_needle:
        mapping_needle = needle
    capability_by_member = {
        member: capability
        for capability in catalog["capabilities"]
        for member in capability["members"]
    }
    mapping_hits: dict[str, dict[str, list[dict[str, Any]]]] = {
        capability["id"]: {"fields": [], "values": []}
        for capability in catalog["capabilities"]
    }
    for member, mapping in catalog["fieldMappings"].items():
        scored_terms = [
            (score, term)
            for term in _mapping_terms(member, mapping)
            if (score := max(_term_score(mapping_needle, term), _term_score(needle, term)))
        ]
        if not scored_terms:
            continue
        score, matched_term = max(scored_terms)
        capability = capability_by_member[member]
        mapping_hits[capability["id"]]["fields"].append(
            {
                "member": member,
                "zh": mapping["zh"],
                "matchedTerm": matched_term,
                "score": score,
            }
        )
    for mapping_key, mapping in catalog["valueMappings"].items():
        member, value = mapping_key.split("::", 1)
        scored_terms = [
            (score, term)
            for term in _mapping_terms(value, mapping)
            if (score := max(_term_score(mapping_needle, term), _term_score(needle, term)))
        ]
        if not scored_terms:
            continue
        score, matched_term = max(scored_terms)
        capability = capability_by_member[member]
        mapping_hits[capability["id"]]["values"].append(
            {
                "member": member,
                "value": value,
                "zh": mapping["zh"],
                "matchedTerm": matched_term,
                "score": score,
            }
        )

    results: list[tuple[int, dict[str, Any]]] = []
    for capability in catalog["capabilities"]:
        candidates = [capability["id"], *capability["members"], *capability["aliases"]]
        candidate_scores = [
            max(_term_score(mapping_needle, candidate), _term_score(needle, candidate))
            for candidate in candidates
        ]
        fallback_score = max(candidate_scores, default=0)
        hits = mapping_hits[capability["id"]]
        concrete_hits = [*hits["fields"], *hits["values"]]
        if concrete_hits:
            strongest = max(hit["score"] for hit in concrete_hits)
            threshold = strongest - 20
            fields = [hit for hit in hits["fields"] if hit["score"] >= threshold]
            values = [hit for hit in hits["values"] if hit["score"] >= threshold]
            score = 200 + strongest + len(fields) * 5 + len(values) * 10
            resolved = dict(capability)
            resolved["matchedMappings"] = {
                "actions": actions,
                "fields": fields,
                "values": values,
            }
        else:
            score = fallback_score
            resolved = dict(capability)
        if score:
            resolved["suggestedMutation"] = _suggested_mutation(catalog, resolved, platform)
            results.append((score, resolved))
    return sorted(results, key=lambda item: (-item[0], item[1]["id"]))


def format_capability_markdown(
    catalog: dict[str, Any],
    capability: dict[str, Any],
    *,
    platform: str,
) -> str:
    state = capability["platforms"][platform]
    source = catalog["configurationSource"]
    source_text = ", ".join(f"{name}: `{path}`" for name, path in source.items())
    enum_text = ", ".join(str(value) for value in capability["enumValues"]) or "无固定枚举"
    constraint_text = "；".join(capability["constraints"]) or "无额外约束"
    dependency_text = ", ".join(capability["dependencies"]) or "无"
    conflict_text = ", ".join(capability["conflicts"]) or "无"
    lines = [
            f"## {capability['id']}",
            "",
            f"- 路线/平台：`{catalog['track']}` / `{platform}`",
            f"- 配置成员：{', '.join(f'`{member}`' for member in capability['members'])}",
            f"- 用户配置入口：{source_text}",
            f"- 修改位置：{capability['mutationTarget']}",
            f"- 类型/默认值：`{capability['type']}` / `{json.dumps(capability['default'], ensure_ascii=False)}`",
            f"- 枚举：{enum_text}",
            f"- 约束：{constraint_text}",
            f"- 依赖：{dependency_text}",
            f"- 冲突：{conflict_text}",
            f"- 已验证版本：`{state['version']}`",
            f"- 状态/证据：`{state['status']}` / `{state['evidence']}`",
            f"- 实际行为：{state['behavior']}",
            f"- 替代方案：{capability['alternative'] or '无'}",
            f"- 验证方法：{capability['verification']}",
        ]
    matched = capability.get("matchedMappings")
    if matched:
        action_text = "、".join(
            f"`{item['term']}` -> `{item['action']}`"
            for item in matched["actions"]
        ) or "未指定操作，仅查询配置"
        lines.extend(["", f"- 识别操作：{action_text}"])
        if matched["fields"]:
            lines.append("- 中英文字段映射：")
            lines.extend(
                f"  - `{item['zh']}` ↔ `{item['member']}`（命中：`{item['matchedTerm']}`）"
                for item in matched["fields"]
            )
        if matched["values"]:
            lines.append("- 中英文值映射：")
            lines.extend(
                f"  - `{item['zh']}` ↔ `{item['value']}`，所属 `{item['member']}`（命中：`{item['matchedTerm']}`）"
                for item in matched["values"]
            )
    suggestion = capability.get("suggestedMutation")
    if suggestion:
        lines.extend(
            [
                "",
                f"- 目标文件：{', '.join(f'`{path}`' for path in suggestion['targetFiles'])}",
                f"- 建议修改：{suggestion['instruction']}",
                f"- 是否允许按当前版本自动修改：`{str(suggestion['allowed']).lower()}`",
                "- 修改后生效指令：",
            ]
        )
        lines.extend(f"  - `{command}`" for command in suggestion["applyCommands"])
    return "\n".join(lines)
