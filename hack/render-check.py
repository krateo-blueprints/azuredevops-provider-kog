#!/usr/bin/env python3
"""Render every RestDefinition through oasgen-provider's own generator and check the result.

oasgen-render ships in the oasgen-provider image (/bin/oasgen-render) and runs the controller's
generation code without a cluster. Feeding it the chart's RestDefinitions and their OAS documents
gives the exact CRDs a cluster would get, so this check fails a PR on:

  1. any generation ERROR (severity "error": the controller would apply nothing);
  2. a query parameter of any verb surfacing as a spec field. oasgen merges the parameters of
     EVERY verb into the spec (oasgen-provider#498), and excludedSpecFields is immutable once
     generated, so a missed exclusion is a permanent wart. A query parameter bound by a verb's
     fieldMapping (inQuery) is not a spec field and is allowed;
  3. the kinds enum in values.schema.json disagreeing with the kinds the templates guard.

Warnings are printed, not fatal: a few are known false positives (e.g. identifiers reached via
allOf, oasgen-provider#483).

Deliberate exceptions to (2) live in hack/render-check-allow.yaml, each with a stated reason.

  4. the config chart's objects failing the generated Configuration CRD schemas (missing or extra
     verbs, wrong auth shape), or the config chart missing a kind.

Usage: hack/render-check.py <rendered-chart.yaml> <chart-dir> <render-url> [rendered-config-chart.yaml]
  rendered-chart.yaml   `helm template` output of the chart (with CHART_VERSION substituted)
  render-url            e.g. http://localhost:8081/render
"""
import json, os, re, sys, urllib.request

import yaml


def validate(obj, schema, where, errs):
    """Structural-schema check: types, required fields, and no unknown fields (the API server
    prunes or rejects those), for the subset Configuration CRDs use."""
    t = schema.get("type")
    if t == "object" or "properties" in schema:
        if not isinstance(obj, dict):
            errs.append(f"{where}: expected object"); return
        props = schema.get("properties", {})
        for r in schema.get("required", []):
            if r not in obj:
                errs.append(f"{where}.{r}: required")
        if not schema.get("x-kubernetes-preserve-unknown-fields") and "additionalProperties" not in schema:
            for k in obj:
                if k not in props:
                    errs.append(f"{where}.{k}: unknown field (the generated CRD does not declare it)")
        for k, v in obj.items():
            if k in props:
                validate(v, props[k], f"{where}.{k}", errs)
    elif t == "string" and not isinstance(obj, str):
        errs.append(f"{where}: expected string, got {type(obj).__name__}")


def main(rendered, chart_dir, url, config_rendered=None):
    docs = [d for d in yaml.safe_load_all(open(rendered)) if d]
    rds = [d for d in docs if d.get("kind") == "RestDefinition"]
    cms = {(d["metadata"].get("namespace", ""), d["metadata"]["name"]): d for d in docs if d.get("kind") == "ConfigMap"}
    oas = {}
    for rd in rds:
        path = rd["spec"]["oasPath"]
        m = re.fullmatch(r"configmap://([^/]+)/([^/]+)/(.+)", path)
        if not m:
            sys.exit(f"{rd['metadata']['name']}: oasPath {path} is not a configmap:// path")
        ns, name, key = m.groups()
        cm = cms.get((ns, name)) or cms.get(("", name))
        if not cm or key not in cm.get("data", {}):
            sys.exit(f"{rd['metadata']['name']}: {path} has no matching ConfigMap/key in the render")
        oas[path] = cm["data"][key]

    req = json.dumps({"restDefinitions": rds, "oas": oas}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=req, headers={"Content-Type": "application/json"}), timeout=120) as r:
        res = json.load(r)

    failures = []
    for e in res.get("errors") or []:
        line = f"{e.get('restDefinition')}: {e.get('field', '')}: {e.get('message')}"
        if e.get("severity") == "error":
            failures.append("generation error: " + line)
        else:
            print("warning:", line)
    for s in res.get("skippedSecuritySchemes") or []:
        print(f"info: {s.get('restDefinition')}: skipped security scheme {s.get('scheme')}")

    # 2. no verb query parameter in any generated spec, unless bound by an inQuery fieldMapping
    crds = {c["spec"]["names"]["kind"]: c for c in res.get("crds") or []}
    allow = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "render-check-allow.yaml"))) or {}
    for k, fields in allow.items():
        for f, why in fields.items():
            if not str(why).strip():
                failures.append(f"render-check-allow.yaml: {k}.{f} has no reason")
    for rd in rds:
        kind = rd["spec"]["resource"]["kind"]
        crd = crds.get(kind)
        if not crd:
            failures.append(f"{kind}: no CRD rendered")
            continue
        doc = yaml.safe_load(oas[rd["spec"]["oasPath"]])
        spec_fields = set()
        for v in crd["spec"]["versions"]:
            spec_fields |= set(v["schema"]["openAPIV3Schema"]["properties"]["spec"].get("properties", {}))
        params = doc.get("components", {}).get("parameters", {})
        for verb in rd["spec"]["resource"]["verbsDescription"]:
            op = doc["paths"][verb["path"]][verb["method"].lower()]
            bound = {fm["inQuery"] for fm in verb.get("fieldMapping") or [] if fm.get("inQuery")}
            bound |= set((allow.get(kind) or {}).keys())
            for p in op.get("parameters", []):
                if "$ref" in p:
                    p = params[p["$ref"].rsplit("/", 1)[1]]
                if p.get("in") != "query" or p["name"] in bound or p["name"] == "api-version":
                    continue
                if p["name"] in spec_fields:
                    failures.append(f"{kind}: query parameter '{p['name']}' of {verb['action']} is a spec field; "
                                    "add it to excludedSpecFields (immutable: before the first release) or bind it")

    # 3. kinds enum == guarded kinds
    schema = json.load(open(os.path.join(chart_dir, "values.schema.json")))
    enum = set(schema["properties"]["kinds"]["items"].get("enum", []))
    guarded = set()
    for fn in os.listdir(os.path.join(chart_dir, "templates")):
        guarded |= set(re.findall(r'kindEnabled" \(list \. "([A-Za-z]+)"\)', open(os.path.join(chart_dir, "templates", fn)).read()))
    rendered_kinds = {rd["spec"]["resource"]["kind"] for rd in rds}
    if enum != guarded:
        failures.append(f"values.schema.json kinds enum {sorted(enum)} != guarded kinds {sorted(guarded)}")
    if rendered_kinds != guarded:
        failures.append(f"rendered kinds {sorted(rendered_kinds)} != guarded kinds {sorted(guarded)}")

    # 4. config-chart output validates against the generated Configuration CRDs
    if config_rendered:
        ccrds = {c["spec"]["names"]["kind"]: c for c in res.get("configurationCrds") or []}
        seen = set()
        for obj in (d for d in yaml.safe_load_all(open(config_rendered)) if d):
            k = obj["kind"]
            seen.add(k)
            crd = ccrds.get(k)
            if not crd:
                failures.append(f"config-chart renders {k}, which no RestDefinition generates"); continue
            errs = []
            spec_schema = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["spec"]
            validate(obj.get("spec", {}), spec_schema, f"{k}.spec", errs)
            # The CRD does not mark the per-verb blocks required, but a verb without its block
            # sends no api-version and Azure DevOps rejects the call: every declared verb is needed.
            q_schema = spec_schema.get("properties", {}).get("configuration", {}).get("properties", {}).get("query", {})
            q_obj = obj.get("spec", {}).get("configuration", {}).get("query", {})
            for verb in q_schema.get("properties", {}):
                if verb not in q_obj:
                    errs.append(f"{k}.spec.configuration.query.{verb}: missing (the {verb} verb would send no api-version)")
            failures += [f"config-chart: {e}" for e in errs]
        for k in sorted(set(ccrds) - seen):
            failures.append(f"config-chart renders no {k}")

    print(f"rendered {len(rds)} RestDefinitions -> {len(crds)} CRDs, {len(res.get('configurationCrds') or [])} Configuration CRDs")
    for f in failures:
        print("FAIL:", f)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    main(*sys.argv[1:])
