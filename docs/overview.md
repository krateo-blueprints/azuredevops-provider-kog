---
type: Architecture
title: azuredevops-provider-kog — overview
description: How azuredevops-provider-kog works — RestDefinitions plus trimmed Azure DevOps OpenAPI documents that oasgen-provider 0.54.0 turns into azuredevops.krateo.io CRDs and one controller per kind — and the design decisions and phase plan behind it.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [krateo, kog, oasgen-provider, rest-dynamic-controller, azure-devops]
timestamp: 2026-11-07T00:00:00Z
---

# Overview

## How it works

The chart renders, per kind, one `ConfigMap` holding a trimmed OpenAPI document and one
`RestDefinition` (`ogen.krateo.io/v1alpha1`) pointing at it. oasgen-provider generates the resource
CRD (its version derived from the document's `info.version`) and a `<Kind>Configuration` CRD
(always `v1alpha1`), then deploys a rest-dynamic-controller for the kind. The chart itself runs
nothing.

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| oasgen-provider | `krateo-platformops/oasgen-provider` **0.54.0**, which pins the provider and rest-dynamic-controller together | The only maintained line. Since 0.35.0 both components share one version, so there is no separate controller floor. |
| API group | `azuredevops.krateo.io` | The family convention (`github.krateo.io`). This makes the chart **mutually exclusive** with the classic provider on one cluster; [usage](./usage.md) has the migration. |
| Kind names | Singular: `Group`, `User`, `SecureFile`, `VariableGroup`, `ServiceEndpoint` | Kubernetes convention. The classic provider used `Groups`, `Users`, `SecureFiles`, `VariableGroups`, `Endpoint`. |
| References | Azure DevOps names or ids, not Kubernetes `*Ref`s | A RestDefinition resolves values from its own CR. Most ADO paths accept a project or repository name in place of its id. |
| Name→id lookups (identity descriptors, agent pools) | Native `dependentLookups` | The lookup and the write stay in one CR, with one status and one drift comparison. An ambiguous match is a hard error. |
| Repository initialisation | A dedicated `GitPush` kind | A push is its own observable object (`pushId`, readable via GET). Hiding it inside `GitRepository` would take it out of status and drift. |
| Pipeline | The whole kind sits on the `build/definitions` API | The update is a PUT of the full definition plus `revision`. Generating the spec from the definition body means the CR already carries the full representation. |
| No plugin | Response reshaping (`responseTransform`), `fieldMapping` (incl. `defaultIfAbsent`), `async`, pagination | These replace every job the legacy plugin did: folder prefix, `allPipelines`, `defaultBranch`. |

## Conventions every kind follows

- **Auth:** basic auth with a PAT (in `password`), declared as an OAS `securityScheme`.
- **`api-version`:** a `configurationFields` entry, so it lives in the Configuration.
- **Lists:** ADO wraps collections as `{count, value: [...]}`, so `findby` declares `itemsPath: value`.
  Where ADO paginates, `findby` declares `continuationToken` pagination (query `continuationToken`,
  response header `x-ms-continuationtoken`). A findby that stops early would create duplicates.
- **Multi-identifier findby:** always `identifiersMatchPolicy: AND` (oasgen-provider #444: with
  the `OR` default, a CR can adopt, and on delete destroy, the wrong resource).
- **Drift:** `compareScope: updatable` wherever create and update bodies differ, and
  `identifiersAndStatus` for immutable kinds without an update verb (`GitPush`, `Run`).
- **Hosts:** core (`dev.azure.com`), Graph and identities (`vssps.dev.azure.com`) and feeds
  (`feeds.dev.azure.com`) each get their own document `servers` entry.

## Phase plan

| Phase | Scope | Exit criterion |
|---|---|---|
| 0 | Repo scaffold, docs, generic CI | This bundle passes lint-docs |
| 1 | `GitRepository`, `GitPush`, `Pipeline`, `PipelinePermission`, plus an `oasgen-render` CI gate, the config chart and kind-specific checks | The three legacy-KOG kinds work natively against a live test org |
| 2 | `TeamProject` (async), `Environment`, `Queue`, `Team`, `CheckConfiguration`, `PullRequest`, `Policy`, `ServiceEndpoint`, `VariableGroup`, `Feed` | Full lifecycle live per kind |
| 3 | `Group`, `User`, `GroupMembership`, `RepositoryPermission`, `FeedPermission` | Permission deletes wait on oasgen-provider #490 |
| 4 | `Run`, `SecureFile` (observe and delete only) | Full lifecycle live per kind |
| 5 | Migration guides, deprecation of the predecessors, first release | — |

Live testing means: create, then no drift over two poll intervals, update, delete, and re-adoption
by `findby`, all against a dedicated throwaway Azure DevOps organisation.

## Known upstream dependencies

- **oasgen-provider #490.** A delete whose query parameter comes from a lookup is sent without
  it when the lookup fails. This blocks the `delete` verb of `RepositoryPermission` and `FeedPermission`.
- **oasgen-provider #323.** A lookup referent that never appears (for example a mistyped
  identity) leaves the CR Pending, with no way to tell "not yet" from "never".
