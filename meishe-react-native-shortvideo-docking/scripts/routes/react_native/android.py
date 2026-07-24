"""React Native Android integration steps."""

from pathlib import Path

from . import implementation
from meishe_docking_core import Report


def validate_package_runtime(target_root: Path, source_plugin: Path, report: Report) -> None:
    implementation.validate_react_native_android_native_libraries(target_root, source_plugin, report)


def integrate(target_root: Path, plugin: Path, source_plugin: Path, report: Report) -> None:
    implementation.merge_react_native_android_permissions(target_root, report)
    implementation.enable_react_native_androidx_jetifier(target_root, report)
    implementation.add_react_native_android_repositories(target_root, report)
    implementation.copy_react_native_plugin_aars(target_root, plugin, report, source_plugin)
    implementation.patch_react_native_app_aars(target_root, report)
    implementation.patch_react_native_plugin_gradle(target_root, plugin, report, source_plugin)
    implementation.patch_react_native_android_publish_bridge(target_root, plugin, report, source_plugin)
