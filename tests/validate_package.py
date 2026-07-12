#!/usr/bin/env python3
from __future__ import annotations

import configparser
import py_compile
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []

for script in ROOT.glob("apps/TA-pihole/bin/*.py"):
    try:
        py_compile.compile(str(script), doraise=True)
    except Exception as exc:
        errors.append(f"{script}: {exc}")

for xml_file in ROOT.glob("apps/SA-pihole/default/data/ui/**/*.xml"):
    try:
        ET.parse(xml_file)
    except Exception as exc:
        errors.append(f"{xml_file}: {exc}")

for conf_file in ROOT.glob("apps/**/*.conf"):
    parser = configparser.RawConfigParser(strict=False)
    try:
        parser.read(conf_file, encoding="utf-8")
    except Exception as exc:
        errors.append(f"{conf_file}: {exc}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)

print("Package validation passed")
