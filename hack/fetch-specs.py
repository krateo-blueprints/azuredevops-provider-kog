#!/usr/bin/env python3
"""Fetch the archived Azure DevOps spec files that the recipes pin, by SWHID.

github.com/MicrosoftDocs/vsts-rest-api-specs no longer exists. Software Heritage archived it
(last full visit 2026-09-12, revision swh:1:rev:c7e66d986b369dce462d04c02288a6c26c155002).
Every recipe in hack/oas-recipes/ pins its source file by content SWHID, so this script fetches
exactly those blobs, nothing resolved by name, and verifies each against its hash.

Usage: hack/fetch-specs.py <recipes-dir> <out-specs-dir>
Writes <out-specs-dir>/<area>/<file>. Anonymous SWH API calls are rate-limited (~120/h), so
already-present files whose hash matches are not re-fetched.
"""
import hashlib, os, sys, time, urllib.error, urllib.request

import yaml

API = "https://archive.softwareheritage.org/api/1"


def blob_swhid(raw):
    return "swh:1:cnt:" + hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


def fetch(swhid):
    url = f"{API}/content/sha1_git:{swhid.rsplit(':', 1)[1]}/raw/"
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            raise
    sys.exit(f"fetch-specs: {swhid}: still rate-limited after retries")


def main(recipes, out):
    wanted = {}
    for fn in sorted(os.listdir(recipes)):
        if fn.endswith(".yaml"):
            recipe = yaml.safe_load(open(os.path.join(recipes, fn)))
            for src in [recipe["source"]] + recipe.get("include", []):
                prev = wanted.setdefault((src["area"], src["file"]), src["swhid"])
                if prev != src["swhid"]:
                    sys.exit(f"fetch-specs: {src['area']}/{src['file']} pinned to two different SWHIDs")
    for (area, name), swhid in sorted(wanted.items()):
        path = os.path.join(out, area, name)
        if os.path.exists(path) and blob_swhid(open(path, "rb").read()) == swhid:
            continue
        raw = fetch(swhid)
        if blob_swhid(raw) != swhid:
            sys.exit(f"fetch-specs: {area}/{name}: archive returned content that does not match {swhid}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(raw)
        print(f"{area}/{name} {swhid}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
