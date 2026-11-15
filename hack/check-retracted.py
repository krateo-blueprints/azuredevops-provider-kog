#!/usr/bin/env python3
"""Refuse a pin on an oasgen-provider version its publisher has retracted.

oasgen-provider publishes the versions that must not be pinned in retracted-versions.yaml at its
repository root. installer's CI enforces that list; this chart pins oasgen-provider directly, so
without this check nothing stops a release from pinning a withdrawn version (chart 0.7.0 pinned
0.66.0, retracted by oasgen-provider#674).

    check-retracted.py [--version V] [--list-url URL]

The pinned version defaults to the tag of $OASGEN_IMAGE, the reference the chart is rendered and
tested against. Exit 0: not retracted. Exit 1: retracted (the entry's `use:` and reason are
printed). Exit 2: the list could not be read or parsed. That fails CLOSED: a list that cannot be
read must not read as "nothing retracted".
"""
import argparse
import os
import sys
import urllib.request

import yaml

LIST_URL = "https://raw.githubusercontent.com/krateo-platformops/oasgen-provider/main/retracted-versions.yaml"
CHART = "oasgen-provider"  # a chart name, as the list's `charts` field expects (not a component name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=os.environ.get("OASGEN_IMAGE", "").rpartition(":")[2])
    ap.add_argument("--list-url", default=LIST_URL)
    a = ap.parse_args()
    if not a.version:
        print("::error::no version: set OASGEN_IMAGE or pass --version")
        return 2
    try:
        with urllib.request.urlopen(a.list_url, timeout=30) as r:
            doc = yaml.safe_load(r.read())
        entries = doc["retracted"]
        if not isinstance(entries, list):
            raise ValueError("'retracted' is not a list")
    except Exception as e:  # fail closed
        print("::error::cannot read %s (%s); refusing rather than assuming nothing is retracted" % (a.list_url, e))
        return 2
    print("read %d retracted entr%s from %s" % (len(entries), "y" if len(entries) == 1 else "ies", a.list_url))
    for e in entries:
        if str(e.get("version")) == a.version and CHART in (e.get("charts") or []):
            print("::error::oasgen-provider %s is RETRACTED; use %s. Reason: %s"
                  % (a.version, e.get("use"), " ".join(str(e.get("reason", "")).split())))
            return 1
    print("oasgen-provider %s is not retracted" % a.version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
