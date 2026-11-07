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
  include: [{area, file, swhid, keep: {<path>: [methods]}}]
                                  optional: operations taken from ANOTHER archived file, merged in
                                  (e.g. an async poll endpoint, which oasgen-provider requires to be
                                  a path of the same document). A definition both files declare must
                                  be identical, or the run fails rather than pick one.
  operationSecurity: <name>       optional HYGIENE: every kept operation declares this
                                  securityDefinitions entry instead of the source's oauth2-only one
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
            # x-ms-examples holds relative $refs to example files (./httpExamples/...) that are not
            # shipped; a parser that resolves them would fail. They carry no contract, so drop them.
            item[m].pop("x-ms-examples", None)
        for k, v in src["paths"][path].items():  # path-item level parameters, if any
            if k not in METHODS:
                item[k] = copy.deepcopy(v)
        out["paths"][path] = item
    # 0a. include: operations from other archived files, with their own closure
    for inc in recipe.get("include", []):
        isrc = load_source(specs, inc)
        if isrc.get("swagger") != src.get("swagger"):
            die(f"include {inc['file']}: format {isrc.get('swagger')} differs from the source's")
        part = {"paths": {}}
        for path, methods in inc["keep"].items():
            if path in out["paths"]:
                die(f"include {inc['file']}: path {path} is already kept from the source")
            if path not in isrc["paths"]:
                die(f"include {inc['file']}: path {path} is not in that file")
            part["paths"][path] = {m: copy.deepcopy(isrc["paths"][path][m]) for m in methods}
            for m in methods:
                part["paths"][path][m].pop("x-ms-examples", None)
        closure(part, isrc)
        out["paths"].update(part["paths"])
        for section in ("definitions", "parameters"):
            for name, val in part.get(section, {}).items():
                have = out.setdefault(section, {}).get(name) or (src.get(section, {}).get(name) if name in src.get(section, {}) else None)
                if have is not None and have != val:
                    die(f"include {inc['file']}: {section}/{name} differs between the two files")
                out[section][name] = val
    # 0. operationSecurity: HYGIENE. The source overrides the top-level basic scheme with an
    #    oauth2-only requirement on every operation. oasgen-provider reads only the document-level
    #    security definitions, so this does not change generation; it keeps the document truthful
    #    for a provider that authenticates every operation with a PAT over basic auth.
    sec = recipe.get("operationSecurity")
    if sec:
        if sec not in out.get("securityDefinitions", {}):
            die(f"operationSecurity: '{sec}' is not a securityDefinitions entry of the source")
        for item in out["paths"].values():
            for m in METHODS:
                if m in item:
                    item[m]["security"] = [{sec: []}]
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
    # 5. a fixed top-level order, so the output does not depend on reference-walk order
    order = ["swagger", "info", "host", "basePath", "schemes", "consumes", "produces",
             "securityDefinitions", "security", "paths", "parameters", "definitions"]
    return {k: out[k] for k in order if k in out}


PARAM_SCHEMA_KEYS = ("type", "format", "items", "enum", "default", "minimum", "maximum", "pattern",
                     "minLength", "maxLength", "minItems", "maxItems", "uniqueItems", "multipleOf")


def rewrite_refs(node):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                v = v.replace("#/definitions/", "#/components/schemas/").replace("#/parameters/", "#/components/parameters/")
            out[k] = rewrite_refs(v)
        return out
    if isinstance(node, list):
        return [rewrite_refs(v) for v in node]
    return node


def check_schema_v2_only(node, where):
    """Fail on Swagger 2.0 schema constructs whose OpenAPI 3.0 meaning differs, rather than guess."""
    if isinstance(node, dict):
        if isinstance(node.get("discriminator"), str):
            die(f"{where}: Swagger 2.0 string discriminator has no 1:1 OpenAPI 3.0 form; convert it explicitly")
        if node.get("type") == "file":
            die(f"{where}: Swagger 2.0 'type: file' is not supported by this converter")
        for k, v in node.items():
            check_schema_v2_only(v, f"{where}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            check_schema_v2_only(v, f"{where}/{i}")


def convert_param(p, where):
    if "$ref" in p:
        return {"$ref": p["$ref"]}
    if p.get("in") == "formData":
        die(f"{where}: formData parameters are not supported by this converter")
    if p.get("in") == "body":
        die(f"{where}: body parameter reached convert_param")
    if "collectionFormat" in p and p["collectionFormat"] not in ("csv",):
        die(f"{where}: collectionFormat {p['collectionFormat']} needs an explicit style/explode mapping")
    q = {k: v for k, v in p.items() if k not in PARAM_SCHEMA_KEYS and k != "collectionFormat"}
    schema = {k: p[k] for k in PARAM_SCHEMA_KEYS if k in p}
    if schema:
        q["schema"] = schema
    if p.get("type") == "array" and p.get("in") == "query":
        q["style"], q["explode"] = "form", False  # Swagger 2.0 default collectionFormat is csv
    return q


def to_oas3(doc):
    """Translate a trimmed Swagger 2.0 document into OpenAPI 3.0.3, covering the subset these specs
    use. Anything outside that subset fails loudly (see check_schema_v2_only / convert_param)."""
    check_schema_v2_only(doc, "")
    consumes = doc.get("consumes", ["application/json"])
    produces = doc.get("produces", ["application/json"])
    scheme = (doc.get("schemes") or ["https"])[0]
    base = (doc.get("basePath") or "/").rstrip("/")
    out = {"openapi": "3.0.3", "info": doc["info"], "servers": [{"url": f"{scheme}://{doc['host']}{base}"}]}
    if "security" in doc:
        out["security"] = doc["security"]
    paths = {}
    for path, item in doc["paths"].items():
        new_item = {}
        for k, v in item.items():
            if k == "parameters":
                new_item[k] = [convert_param(p, f"{path}/parameters") for p in v]
                continue
            if k not in METHODS:
                new_item[k] = v
                continue
            op = {key: val for key, val in v.items() if key not in ("parameters", "responses", "consumes", "produces")}
            params = []
            for p in v.get("parameters", []):
                if p.get("in") == "body":
                    op["requestBody"] = {
                        **({"description": p["description"]} if p.get("description") else {}),
                        "required": bool(p.get("required", False)),
                        "content": {mt: {"schema": p["schema"]} for mt in v.get("consumes", consumes)},
                    }
                else:
                    params.append(convert_param(p, f"{k.upper()} {path}"))
            if params:
                op["parameters"] = params
            responses = {}
            for code, r in v.get("responses", {}).items():
                nr = {"description": r.get("description", "")}
                if "schema" in r:
                    nr["content"] = {mt: {"schema": r["schema"]} for mt in v.get("produces", produces)}
                if "headers" in r:
                    nr["headers"] = {h: {**({"description": hv["description"]} if hv.get("description") else {}),
                                         "schema": {kk: hv[kk] for kk in PARAM_SCHEMA_KEYS if kk in hv}}
                                     for h, hv in r["headers"].items()}
                responses[str(code)] = nr
            op["responses"] = responses
            new_item[k] = op
        paths[path] = new_item
    out["paths"] = paths
    comps = {}
    if "parameters" in doc:
        comps["parameters"] = {n: convert_param(p, f"parameters/{n}") for n, p in doc["parameters"].items()}
    if "definitions" in doc:
        comps["schemas"] = doc["definitions"]
    schemes = {}
    for name, s in (doc.get("securityDefinitions") or {}).items():
        desc = {"description": s["description"]} if s.get("description") else {}
        if s["type"] == "basic":
            schemes[name] = {"type": "http", "scheme": "basic", **desc}
        elif s["type"] == "apiKey":
            schemes[name] = {"type": "apiKey", "name": s["name"], "in": s["in"], **desc}
        elif s["type"] == "oauth2":
            flow = {"accessCode": "authorizationCode", "implicit": "implicit",
                    "password": "password", "application": "clientCredentials"}[s["flow"]]
            f = {"scopes": s.get("scopes", {})}
            if "authorizationUrl" in s:
                f["authorizationUrl"] = s["authorizationUrl"]
            if "tokenUrl" in s:
                f["tokenUrl"] = s["tokenUrl"]
            schemes[name] = {"type": "oauth2", "flows": {flow: f}, **desc}
        else:
            die(f"securityDefinitions/{name}: type {s['type']} not supported by this converter")
    if schemes:
        comps["securitySchemes"] = schemes
    if comps:
        out["components"] = comps
    return rewrite_refs(out)


def render(specs, recipe_path):
    recipe = yaml.safe_load(open(recipe_path))
    doc = to_oas3(trim(specs, recipe))
    head = [
        "# GENERATED by hack/trim-oas.py from hack/oas-recipes/" + os.path.basename(recipe_path) + " -- do not edit by hand.",
        f"# Source: {recipe['source']['area']}/{recipe['source']['file']} ({recipe['source']['swhid']})",
        "#   from the Software Heritage archive of github.com/MicrosoftDocs/vsts-rest-api-specs",
        "# Converted from Swagger 2.0 to OpenAPI 3.0.3 (hack/trim-oas.py to_oas3): rest-dynamic-controller",
        "#   0.54.x loads OpenAPI 3 only (oasgen-provider#499). The conversion changes format, not content.",
        "# Deliberate departures from the source (see the recipe for each reason):",
    ]
    head.append("#   x-ms-examples removed from every operation (relative refs to unshipped example files)")
    if recipe.get("operationSecurity"):
        head.append(f"#   operationSecurity: every operation declares {recipe['operationSecurity']} (hygiene; inert for oasgen-provider)")
    for inc in recipe.get("include", []):
        head.insert(3, f"# Included: {', '.join(inc['keep'])} from {inc['area']}/{inc['file']} ({inc['swhid']})")
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
