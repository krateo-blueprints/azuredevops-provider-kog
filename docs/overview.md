---
type: Architecture
title: azuredevops-provider-kog — overview
description: How azuredevops-provider-kog works — RestDefinitions plus trimmed Azure DevOps OpenAPI documents that oasgen-provider 0.55.0 turns into azuredevops.krateo.io CRDs and one controller per kind — and the design decisions and phase plan behind it.
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
| oasgen-provider | `krateo-platformops/oasgen-provider` **0.55.0**, which pins the provider and rest-dynamic-controller together | The only maintained line. Since 0.35.0 both components share one version, so there is no separate controller floor. |
| API group | `azuredevops.krateo.io` | The family convention (`github.krateo.io`). This makes the chart **mutually exclusive** with the classic provider on one cluster; [usage](./usage.md) has the migration. |
| Kind names | Singular: `Group`, `User`, `SecureFile`, `VariableGroup`, `ServiceEndpoint` | Kubernetes convention. The classic provider used `Groups`, `Users`, `SecureFiles`, `VariableGroups`, `Endpoint`. |
| References | Azure DevOps names or ids, not Kubernetes `*Ref`s | A RestDefinition resolves values from its own CR. Most ADO paths accept a project or repository name in place of its id. |
| Name→id lookups (identity descriptors, agent pools) | Native `dependentLookups` | The lookup and the write stay in one CR, with one status and one drift comparison. An ambiguous match is a hard error. |
| Repository initialisation | A dedicated `GitPush` kind | A push is its own observable object (`pushId`, readable via GET). Hiding it inside `GitRepository` would take it out of status and drift. |
| Pipeline | The whole kind sits on the `build/definitions` API | The update is a PUT of the full definition plus `revision`. Generating the spec from the definition body means the CR already carries the full representation. |
| No plugin | `fieldMapping` (incl. `defaultIfAbsent`), `requestTransform`/`responseTransform`, `async`, pagination | `allPipelines` is filled by `defaultIfAbsent`. The folder prefix is avoided by using Azure DevOps's own path form. `defaultBranch` waits on oasgen-provider#491 (see below). |
| Pipeline folder | `spec.path` in Azure DevOps's own form (`'\team\ci'`, root `'\'`) | What the API stores, so it compares directly with no transform. Another spelling drifts. |
| Repository delete | Azure DevOps's soft delete (recycle bin) | One call, recoverable, and the name is reusable immediately (measured). |
| OpenAPI format | Microsoft's Swagger 2.0, converted to OpenAPI 3.0.3 at build time | rest-dynamic-controller 0.54.x loads OpenAPI 3 only (oasgen-provider#499). The conversion changes format, not content. |

## Where the OpenAPI documents come from

`github.com/MicrosoftDocs/vsts-rest-api-specs` no longer exists. Its last full snapshot is in the
Software Heritage archive (revision `swh:1:rev:c7e66d986b369dce462d04c02288a6c26c155002`). Each
recipe in `hack/oas-recipes/` pins its source file by content SWHID. `hack/fetch-specs.py`
fetches exactly those blobs and verifies their hashes, and `hack/trim-oas.py` keeps the declared
operations, applies the recipe's patches (each must state a reason), and emits OpenAPI 3.0.3. CI
regenerates every asset and fails on any difference.

Departures from Microsoft's document are corrections to what the API actually does, each
measured or documented. Examples: list responses are `{count, value}` envelopes, a push returns
201 rather than 200, and `GitRepositoryCreateOptions.project` is dropped because the URL
addresses the project.

## Conventions every kind follows

- **Project:** `spec.project` is the `{project}` path parameter (name or id), never a body object.
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
| 0 | Repo scaffold, docs, generic CI | ✅ |
| 1 | `GitRepository`, `GitPush`, `Pipeline`, `PipelinePermission`, plus an `oasgen-render` CI gate, the config chart and kind-specific checks | ✅ verified live 2026-11-07 (PipelinePermission without delete) |
| 2a | `TeamProject` (async), `Environment`, `Queue`, `CheckApproval`, `CheckExclusiveLock`, `CheckRequiredTemplate`, `CheckTask` | ✅ verified live 2026-11-07 on 0.54.1 |
| 2b | `PullRequest`, `Policy`, `Feed` | Full lifecycle live per kind |
| 2c | `ServiceEndpoint*` (per auth scheme), `VariableGroup` | Credentials come from Secrets: wait on oasgen-provider#510 |
| held | `Team` | Built and verified; held until offset pagination exists (oasgen-provider#486) |
| 3 | `Group`, `User`, `GroupMembership`, `RepositoryPermission`, `FeedPermission` | Permission deletes wait on oasgen-provider #490 |
| 4 | `Run`, `SecureFile` (observe and delete only) | Full lifecycle live per kind |
| 5 | Migration guides, deprecation of the predecessors, first release | — |

Live testing means: create, then no drift over two poll intervals, update, delete, and re-adoption
by `findby`, all against a dedicated throwaway Azure DevOps organisation.

## Per-kind behaviour (verified live)

| Kind | Observe | Update | Delete | Notes |
|---|---|---|---|---|
| `GitRepository` | findby `name`, then get by `status.id` | PATCH `{name}` (rename) | soft delete (recycle bin) | Adopts an existing repository with the same name. `status.defaultBranch` appears after the first push. |
| `GitPush` | get by `status.pushId` (no findby) | none (immutable) | none (releases the CR) | `oldObjectId` is compare-and-swap, so a retried push is refused (409), never duplicated. See recovery below. |
| `Pipeline` | findby `name`+`path` (AND), then get by `status.id` | PUT with `status.id` + `status.revision` | DELETE | PUT replaces the definition: settings made outside the CR are reset. |
| `PipelinePermission` | get by `{resourceType}/{resourceId}` | PATCH | **none yet** | The GET always returns 200, so the kind converges through update. Deleting a CR leaves the grants (oasgen-provider#502). |
| `TeamProject` | findby `name` (paginated), then get by `status.id` | PATCH (async) | DELETE (async; recycle bin) | Create/update/delete return 202 + an operation, polled with `mode: requeue` (create/update) or inline (delete). `status.id` is briefly empty after an update until findby re-adopts (oasgen-provider#506). |
| `Environment` | findby `name` (server-side filter), then get by `status.id` | PATCH | DELETE | — |
| `Queue` | findby `name` (server-side filter), then get by `status.id` | none | DELETE | **`spec.pool.id` is required for now**: the pool-name lookup is declared but cannot send `api-version` (oasgen-provider#508). |
| `CheckApproval` | findby type + resource (AND), then get by `status.id` with `$expand=settings` | PATCH (full body + `id`) | DELETE | One per resource (measured). `type` is defaulted. |
| `CheckExclusiveLock` | as `CheckApproval` | PATCH | DELETE | One per resource; no settings. |
| `CheckRequiredTemplate` | as `CheckApproval` | PATCH | DELETE | One per resource; `settings.extendsChecks[]`. |
| `CheckTask` | get by `status.id` only (**no findby**) | PATCH | DELETE | Any number per resource, even with equal names (measured), so it never adopts; a lost create response needs manual recovery (oasgen-provider#503). |

### GitPush: recovering a lost create response

GitPush has no findby on purpose: listing pushes by ref matches pushes made by anyone, so a CR
could adopt a push it never made. The cost is that if a create succeeds but its response is lost
(crash, eviction, API error before the status write), the CR has no `pushId`, and the retry is
refused with 409. The push itself happened exactly once. To recover: confirm the push in Azure
DevOps, delete the CR (that only releases it), and stop there. To push again, create a new CR
with `oldObjectId` set to the branch's current head. Tracked upstream as oasgen-provider#503.

## Known upstream dependencies

| Issue | Effect here |
|---|---|
| oasgen-provider#491 | A field only the update body accepts cannot be a spec field: `GitRepository.defaultBranch` waits on it. |
| oasgen-provider#499 | rest-dynamic-controller loads OpenAPI 3 only, so documents are converted. |
| oasgen-provider#502 | No "delete is a reset" for always-present resources: `PipelinePermission` ships without delete. |
| oasgen-provider#503 | A get-only kind cannot recover a lost create response (GitPush recovery is manual). |
| oasgen-provider#490 | A delete whose query parameter comes from a lookup is sent without it when the lookup fails: blocks the `delete` verb of `RepositoryPermission` and `FeedPermission`. |
| oasgen-provider#323 | A lookup referent that never appears (e.g. a mistyped identity) leaves the CR Pending, with no way to tell "not yet" from "never". |
| oasgen-provider#496, #497, #498 | Uninstall leaves `*Configuration` CRDs, informational notices labelled "generation error:", findby query parameters becoming spec fields (all excluded here). |
| oasgen-provider#505 | `async` paths are plain dot notation (`id`, `status`); a leading dot fails silently after the vendor accepted the call. |
| oasgen-provider#506 | An async update's operation response replaces status; `TeamProject` recovers `status.id` through findby. |
| oasgen-provider#507 | Applying a Configuration restarts the controller; `TeamProject` uses `mode: requeue` so a restart never re-sends a create. |
| oasgen-provider#508 | Dependent lookups cannot send `api-version`: `Queue` needs `spec.pool.id`; Phase 3 identity lookups wait. |
| oasgen-provider#510 | Every `secretRef` resource fails on 0.53.0+: the service-connection kinds and secret variables wait. |
| oasgen-provider#486 | No offset pagination (Azure DevOps also needs a short-page signal and cross-page consistency, measured): `Team` is held. |
