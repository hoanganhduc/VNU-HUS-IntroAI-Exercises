#!/usr/bin/env python3
"""Fail closed while the Week 7 assignment remains blocked."""

from __future__ import annotations

import sys


def main() -> int:
    print("FAIL ch07-uncertainty is blocked; no submission contract is defined")
    print("\n0/100 incomplete submission")
    return 1


if __name__ == "__main__":
    sys.exit(main())
