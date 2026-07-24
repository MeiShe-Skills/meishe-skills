#!/usr/bin/env python3
"""React Native entry point for Meishe ShortVideo integration."""

from __future__ import annotations

import sys

from meishe_docking_core import IntegrationError, main_for_platform


if __name__ == "__main__":
    try:
        raise SystemExit(main_for_platform("react-native", sys.argv[1:]))
    except IntegrationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
