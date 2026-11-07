---
type: Component
title: azuredevops-provider-kog — index
description: The map of the azuredevops-provider-kog doc bundle — a Krateo KOG provider that exposes Azure DevOps resources as azuredevops.krateo.io Kubernetes kinds via oasgen-provider 0.54.1, with no plugin.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [krateo, kog, oasgen-provider, azure-devops]
timestamp: 2026-11-07T00:00:00Z
---

# azuredevops-provider-kog

azuredevops-provider-kog is a Krateo **KOG** provider, built on
[`oasgen-provider`](https://github.com/krateo-platformops/oasgen-provider) **0.54.1**. It
exposes Azure DevOps REST resources as Kubernetes kinds under `azuredevops.krateo.io`.

It replaces two unmigrated predecessors. One is the classic, hand-written azuredevops-provider
(19 kinds, Go controllers). The other is the legacy azuredevops-provider KOG chart (3 kinds on
oasgen-provider 0.10 plus a proxy plugin). Every kind here is **native**: no plugin, no image,
no proxy.

> **Status: Phase 1.** Four kinds are native and live-verified against Azure DevOps:
> `GitRepository`, `GitPush`, `Pipeline` and `PipelinePermission`. The rest are planned, and each
> lands in its own PR with live-test evidence.

## The kinds

| Family | Kinds | Phase |
|--------|-------|-------|
| **Repositories** | **`GitRepository`**, **`GitPush`** ✅ · `PullRequest`, `Policy` | 1 / 2 |
| **Pipelines** | **`Pipeline`**, **`PipelinePermission`** ✅ · `Run`, `CheckConfiguration`, `Queue`, `Environment` | 1 / 2 / 4 |
| **Project & config** | `TeamProject`, `ServiceEndpoint`, `VariableGroup`, `SecureFile` | 2 / 4 |
| **Artifacts** | `Feed`, `FeedPermission` | 2 / 3 |
| **Identity & access** | `Team`, `Group`, `User`, `GroupMembership`, `RepositoryPermission` | 2 / 3 |

The classic provider's `ConnectorConfig` has no equivalent. Each kind gets its own generated
`<Kind>Configuration` (basic auth with a PAT, plus `api-version`) instead.

## The bundle (start here)

- [overview](./overview.md) — how it works, the design decisions, and the phase plan.
- [usage](./usage.md) — install, credentials, migration from the predecessors.
- [configuration](./configuration.md) — the chart values and the RestDefinition conventions.
- [api](./api.md) — the generated CRDs.
- [examples](./examples.md) — the runnable examples under `examples/`.
- [release](./release.md) — how a release ships.
- [log](./log.md) — curated history.
- [llms.txt](./llms.txt) — file-by-file index.

## Layout

- `chart/`: the RestDefinitions (`templates/rd-<kind>.yaml`), the OpenAPI documents
  (`assets/<kind>.yaml`, as ConfigMaps) and `values.schema.json`. No Deployment or image.
- `config-chart/`: one `<Kind>Configuration` per kind, all naming one PAT Secret.
- `hack/oas-recipes/`: one recipe per kind. Every `chart/assets/<kind>.yaml` is **generated**
  from Microsoft's archived spec by `hack/trim-oas.py` and never edited by hand.
- `hack/`: the generator and the CI checks (`render-check.py` runs oasgen's own generator).
- `examples/`: runnable examples.
