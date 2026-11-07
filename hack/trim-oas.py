#!/usr/bin/env python3
"""Derive one kind's trimmed OpenAPI document from Microsoft's archived Azure DevOps spec.

WHY. github.com/MicrosoftDocs/vsts-rest-api-specs no longer exists. Its last full snapshot is
in the Software Heritage archive, and every spec file is addressed by an SWHID (a git blob
hash). A trimmed document that cannot be re-derived from a pinned source drifts silently, so
each chart/assets/<kind>.yaml is GENERATED from a recipe (hack/oas-recipes/<kind>.yaml) and
never edited by hand.

A recipe names:
  source:  {area, file, swhid}    the archived file, verified against its SWHID before use
  info:    {title}                the document title (info.version is kept from the source)
  keep:    {<path>: [methods]}    the operations to keep; everything they reference is kept
  patches: [{op, at, value, reason}]
           The deliberate departures from Microsoft's document. `reason` is required:
           a patch without a stated reason fails. `at` is a list of keys/indexes from the
           document root; op is `set` or `delete`.

Usage:
  hack/trim-oas.py <specs-dir> <recipe.yaml> <out.yaml>    write one document
  hack/trim-oas.py --check <specs-dir> <recipes-dir> <assets-dir>
                                                           fail if any asset differs from
                                                           its recipe's output
<specs-dir> holds <area>/<file> as fetched by hack/fetch-specs.py.
"""
import copy, hashlib, json, os, sys

import yaml

METHODS = ("get", "put", "post", "delete", "patch")


def die(msg):
    sys.exit(f"trim-oas: {msg}")


def load_source(specs, src):
    path = os.path.join(specs, src["area"], src["file"])
    raw = open(path, "rb").read()
    got = "swh:1:cnt:" + hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
    if got != src["swhid"]:
        die(f"{path}: content is {got}, recipe pins {src['swhid']}")
    return json.loads(raw.decode("utf-8-sig"))


def refs(node, out):
    if isinstance(node, dict):
        r = node.get("$ref")
        if isinstance(r, str) and r.startswith("#/"):
            out.add(r)
        for v in node.values():
            refs(v, out)
    elif isinstance(node, list):
        for v in node:
            refs(v, out)


def resolve(doc, ref):
    node = doc
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def walk_to(doc, at, create=False):
    node = doc
    for key in at[:-1]:
        if isinstance(node, list):
            node = node[key]
        else:
            if key not in node:
                if not create:
                    die(f"patch path {at}: '{key}' does not exist")
                node[key] = {}
            node = node[key]
    return node


def apply_patch(doc, p):
    if not p.get("reason"):
        die(f"patch {p.get('at')} has no reason; every departure from the source must state one")
    at = p["at"]
    parent = walk_to(doc, at, create=p["op"] == "set")
    last = at[-1]
    if p["op"] == "set":
        parent[last] = copy.deepcopy(p["value"])
    elif p["op"] == "delete":
        if isinstance(parent, list):
            parent.pop(last)
        elif last in parent:
            del parent[last]
        else:
            die(f"patch delete {at}: nothing there")
    else:
        die(f"patch op '{p['op']}' unknown (set|delete)")


def closure(out, src):
    """Copy into `out` every #/definitions or #/parameters entry reachable from its paths that it
    does not already have. Entries already present (possibly patched) are never overwritten."""
    pending = set()
    refs(out["paths"], pending)
    seen = set()
    while pending:
        r = pending.pop()
        if r in seen:
            continue
        seen.add(r)
        section, name = r[2:].split("/", 1)
        bucket = out.setdefault(section, {})
        if name not in bucket:
            bucket[name] = copy.deepcopy(resolve(src, r))
        refs(bucket[name], pending)


def trim(specs, recipe):
    src = load_source(specs, recipe["source"])
    out = {"swagger": src["swagger"], "info": {"title": recipe["info"]["title"], "version": src["info"]["version"]}}
    for k in ("host", "basePath", "schemes", "consumes", "produces", "securityDefinitions", "security"):
        if k in src:
            out[k] = copy.deepcopy(src[k])
    out["paths"] = {}
    for path, methods in recipe["keep"].items():
        if path not in src["paths"]:
            die(f"keep: path {path} is not in {recipe['source']['file']}")
        item = {}
        for m in methods:
            if m not in src["paths"][path]:
                die(f"keep: {m.upper()} {path} is not in the source")
            item[m] = copy.deepcopy(src["paths"][path][m])
        for k, v in src["paths"][path].items():  # path-item level parameters, if any
            if k not in METHODS:
                item[k] = copy.deepcopy(v)
        out["paths"][path] = item
    # 1. pull in everything the kept operations reference, from the source
    closure(out, src)
    # 2. apply the recipe's deliberate departures, in order
    for p in recipe.get("patches", []):
        apply_patch(out, p)
    # 3. a patch may introduce a $ref the source defines: pull it in
    closure(out, src)
    # 4. drop what nothing reachable from the paths references any more
    live, stack = set(), set()
    refs(out["paths"], stack)
    while stack:
        r = stack.pop()
        if r in live:
            continue
        live.add(r)
        refs(resolve(out, r), stack)
    for section in ("definitions", "parameters"):
        if section in out:
            out[section] = {n: v for n, v in sorted(out[section].items()) if f"#/{section}/{n}" in live}
            if not out[section]:
                del out[section]
    return out


def render(specs, recipe_path):
    recipe = yaml.safe_load(open(recipe_path))
    doc = trim(specs, recipe)
    head = [
        "# GENERATED by hack/trim-oas.py from hack/oas-recipes/" + os.path.basename(recipe_path) + " -- do not edit by hand.",
        f"# Source: {recipe['source']['area']}/{recipe['source']['file']} ({recipe['source']['swhid']})",
        "#   from the Software Heritage archive of github.com/MicrosoftDocs/vsts-rest-api-specs",
        "# Deliberate departures from the source (see the recipe for each reason):",
    ]
    for p in recipe.get("patches", []):
        head.append(f"#   {p['op']} {'/'.join(str(a) for a in p['at'])}")
    return "\n".join(head) + "\n" + yaml.safe_dump(doc, sort_keys=False, width=100, allow_unicode=True)


def main(argv):
    if argv[:1] == ["--check"]:
        specs, recipes, assets = argv[1:4]
        bad = 0
        for fn in sorted(os.listdir(recipes)):
            if not fn.endswith(".yaml"):
                continue
            want = render(specs, os.path.join(recipes, fn))
            have_path = os.path.join(assets, fn)
            have = open(have_path).read() if os.path.exists(have_path) else None
            if have != want:
                bad += 1
                print(f"STALE {have_path}: regenerate with hack/trim-oas.py")
        sys.exit(1 if bad else 0)
    if len(argv) != 3:
        sys.exit(__doc__)
    open(argv[2], "w").write(render(argv[0], argv[1]))


if __name__ == "__main__":
    main(sys.argv[1:])
