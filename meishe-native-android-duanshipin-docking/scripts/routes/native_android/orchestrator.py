"""Native Android route; no framework or iOS implementation is loaded."""

from argparse import Namespace
from pathlib import Path

from meishe_docking_core import Report
from .implementation import find_android_root, integrate_native_android, resolve_aar


def integrate_native_android_route(args: Namespace, target_root: Path, report: Report) -> None:
    find_android_root(target_root)
    aar = resolve_aar(args, target_root, report)
    integrate_native_android(args, target_root, aar, report)
