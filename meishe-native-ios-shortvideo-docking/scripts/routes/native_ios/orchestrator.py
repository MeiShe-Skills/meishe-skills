"""Native iOS route; no framework or Android implementation is loaded."""

from argparse import Namespace
from pathlib import Path

from meishe_docking_core import Report
from .implementation import integrate_native_ios


def integrate_native_ios_route(args: Namespace, target_root: Path, report: Report) -> None:
    integrate_native_ios(args, target_root, report)
