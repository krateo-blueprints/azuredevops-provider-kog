---
type: Log
title: azuredevops-provider-kog — log
description: Curated chronological history of azuredevops-provider-kog — notable changes and decisions, not a generated changelog.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [log, history]
timestamp: 2026-11-07T00:00:00Z
---

# Log

Curated history; release notes live in GitHub Releases.

## 2026-11-08 — oasgen-provider 0.55.0

- Pin moved from 0.54.1 to 0.55.0 after a live check: the cluster upgraded in place (CRDs chart,
  then provider chart; every controller rolled, live CRs stayed Ready), then the full scripted
  suite passed 94/94 against Azure DevOps (every shipped kind: create, no drift, update, delete, and
  adoption with drift corrected for every findby kind).
- 0.55.0 fixes oasgen-provider#514: a bracket-escaped `inQuery` binding is recognised as supplying
  its parameter. `PullRequest` keeps the two escaped exclusions; they are now redundant but still
  correct, and `excludedSpecFields` is append-only once released.
- 0.55.0 adds an `AbsenceInferredFromUnmatchedListing` event (oasgen-provider#485): one `Normal`
  event on a findby kind's first create, `Warning` only when absence keeps being inferred for the
  same spec generation. Observed exactly once per create in the suite.

## 2026-11-07 — oasgen-provider 0.54.1

- Re-verified on 0.54.1 before moving the pin: the live cluster upgraded in place (all
  RestDefinitions re-rendered, every controller rolled, every live CR stayed Ready), then a fresh
  full lifecycle of the four Phase 1 kinds passed 21 of 21 checks.
- 0.54.1 persists `status.schemaWarnings` (oasgen-provider#492). None of the issues this
  repository filed is in it; the documented limits are unchanged.

## 2026-11-07 — Phase 1

- Four native kinds, live-verified against a real organisation: `GitRepository` (create, no
  drift, rename, adoption, soft delete, name reuse), `GitPush` (initial and follow-up pushes;
  repository `defaultBranch` set), `Pipeline` (create, no drift, rename via PUT+revision,
  adoption, delete), `PipelinePermission` (grant, spec revoke, drift-free via `defaultIfAbsent`).
- OpenAPI documents generated from Microsoft's spec archived in Software Heritage (the GitHub repo
  is gone) and converted to OpenAPI 3.0.3, because rest-dynamic-controller 0.54.0 cannot load
  Swagger 2.0 (oasgen-provider#499).
- Measured corrections to Microsoft's document: `{count, value}` list envelopes, push returns 201,
  create-body `project` dropped (the URL addresses it), narrowed request schemas for pushes and
  YAML pipelines.
- `PipelinePermission` ships without a delete verb: the permissions GET always returns 200, so
  a revoking delete held the finalizer forever (oasgen-provider#502).
- CI: assets regenerate from recipes; every RestDefinition renders through oasgen-render; query
  parameters cannot leak into specs; the config chart validates against generated CRDs. Each check
  was proven by mutation.
- Upstream issues filed: oasgen-provider #491, #496, #497, #498, #499, #502, #503.

## 2026-11-07 — Phase 0

- Repository scaffolded on the github-provider-kog layout.
- Decisions: oasgen-provider 0.54.0; group `azuredevops.krateo.io` (mutually exclusive with the
  classic provider); singular kind names; native `dependentLookups` for name→id resolution; a
  dedicated `GitPush` kind for repository initialisation; `Pipeline` on `build/definitions`;
  no plugin.
- Filed oasgen-provider #490 (a delete is sent without a lookup-supplied query parameter). It
  blocks the permission kinds' delete verb.
