---
type: Architecture
title: azuredevops-provider-kog — overview
description: How azuredevops-provider-kog works — RestDefinitions plus trimmed Azure DevOps OpenAPI documents that oasgen-provider 0.57.0 turns into azuredevops.krateo.io CRDs and one controller per kind — and the design decisions and phase plan behind it.
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
| oasgen-provider | `krateo-platformops/oasgen-provider` **0.57.0**, which pins the provider and rest-dynamic-controller together | The only maintained line. Since 0.35.0 both components share one version, so there is no separate controller floor. |
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
| 2b | `PullRequest`, `PolicyBuildValidation`, `PolicyRequiredReviewers`, `PolicyStatus`, `Feed` | ✅ verified live 2026-11-08 on 0.54.1 |
| 2c | `ServiceEndpointUsernamePassword`, `ServiceEndpointToken`, `ServiceEndpointGitHubToken`, `ServiceEndpointServicePrincipal` | ✅ verified live 2026-11-09 on 0.56.0; adopting an existing connection verified 2026-11-11 on 0.57.0 |
| planned | `VariableGroup` | Secret variables are a map keyed by user-chosen names, and a `secretRef` addresses one path: needs a map-valued resolver or a wildcard path (to be designed with oasgen-provider) |
| held | `Team` | Built and verified; held until offset pagination exists (oasgen-provider#486) |
| held | `PolicyMinimumReviewers`, `PolicyWorkItemLinking`, `PolicyCommentRequirements`, `PolicyMergeStrategy` | Lifecycle verified; held because they cannot adopt (identity is in `settings.scope[0]`, oasgen-provider#517, #519) |
| 3 | `Group`, `GroupMembership`, `RepositoryPermission`, `FeedPermission` | ✅ verified live 2026-11-08 on 0.55.0 |
| held | `User` | Built and verified for valid principals; held until a failed add (HTTP 200, `isSuccess: false`) can surface (oasgen-provider#529) |
| 4 | `Run` | ✅ verified live 2026-11-08 on 0.54.1 |
| 4 (waits) | `SecureFile` | The upload body is the raw file bytes, from a Secret: waits on oasgen-provider#521 |
| 5 | Migration guides, deprecation of the predecessors, first release | — |

Live testing means: create, then no drift over two poll intervals, update, delete, and re-adoption
by `findby`, all against a dedicated throwaway Azure DevOps organisation.

## Per-kind behaviour (verified live)

| Kind | Observe | Update | Delete | Notes |
|---|---|---|---|---|
| `GitRepository` | findby `name`, then get by `status.id` | PATCH `{name}` (rename) | soft delete (recycle bin) | Adopts an existing repository with the same name. `status.defaultBranch` appears after the first push. |
| `GitPush` | get by `status.pushId` (no findby) | none (immutable) | none (releases the CR) | `oldObjectId` is compare-and-swap, so a retried push is refused (409), never duplicated, within one repository. `repositoryId` must be the repository's GUID (the CRD refuses a name): a name stops resolving on rename, the push's get then answers 404, the push reads as absent and its create is sent again, to whichever repository holds the old name (measured 2026-11-11). See recovery below. |
| `Pipeline` | findby `name`+`path` (AND), then get by `status.id` | PUT with `status.id` + `status.revision` | DELETE | PUT replaces the definition: settings made outside the CR are reset. |
| `PipelinePermission` | get by `{resourceType}/{resourceId}` | PATCH | **none yet** | The GET always returns 200, so the kind converges through update. Deleting a CR leaves the grants (oasgen-provider#502). |
| `TeamProject` | findby `name` (paginated), then get by `status.id` | PATCH (async) | DELETE (async; recycle bin) | Create/update/delete return 202 + an operation, polled with `mode: requeue` (create/update) or inline (delete). `status.id` is briefly empty after an update until findby re-adopts (oasgen-provider#506). |
| `Environment` | findby `name` (server-side filter), then get by `status.id` | PATCH | DELETE | — |
| `Queue` | findby `name` (server-side filter), then get by `status.id` | none | DELETE | **`spec.pool.id` is required for now**: the pool-name lookup is declared but cannot send `api-version` (oasgen-provider#508). |
| `CheckApproval` | findby type + resource (AND), then get by `status.id` with `$expand=settings` | PATCH (full body + `id`) | DELETE | One per resource (measured). `type` is defaulted. |
| `CheckExclusiveLock` | as `CheckApproval` | PATCH | DELETE | One per resource; no settings. |
| `CheckRequiredTemplate` | as `CheckApproval` | PATCH | DELETE | One per resource; `settings.extendsChecks[]`. |
| `CheckTask` | get by `status.id` only (**no findby**) | PATCH | DELETE | Any number per resource, even with equal names (measured), so it never adopts; a lost create response needs manual recovery (oasgen-provider#503). |
| `PullRequest` | findby `sourceRefName`+`targetRefName` (AND, active PRs, filtered server-side), then get by `status.pullRequestId` | PATCH (title, description, draft) | **abandon** (PATCH `status: abandoned`) | One active PR per branch pair (measured). An abandoned PR counts as absent, so a PR abandoned in the UI is re-opened by its CR; a completed PR stays present. `repositoryId` must be the repository's GUID, for the same reason as `GitPush`. |
| `PolicyBuildValidation`, `PolicyRequiredReviewers`, `PolicyStatus` | get by `status.id` only (**no findby**) | PUT (full body) | DELETE (soft: `isDeleted`) | Any number per branch, even identical (measured), so they never adopt. `type` defaulted; `scope[].repositoryId` is the repository GUID. `validDuration` must be 0 unless `queueOnSourceUpdateOnly` is true. |
| `Feed` | findby `name`, then get by `status.id` | PATCH (rename, description, flags) | soft delete (feed recycle bin) | Served from `feeds.dev.azure.com`. **A deleted feed's name stays reserved** (409 on re-create, measured still reserved 10 minutes after purging), so a CR re-created with the same name waits on Azure DevOps. |
| `Run` | get by `status.id` only (**no findby**) | none (a run is immutable) | **none**: deleting the CR releases it and keeps the run | Every POST starts a new run (measured), so it never adopts, and a lost create response re-triggers (oasgen-provider#503). Ready means the run exists; read `status.state`/`status.result`. Cancel can't be a delete (the run stays readable) and DELETE refuses a running run (403). |
| `Group` | findby `displayName` in `scopeDescriptor`, then get by `status.descriptor` | PATCH (RFC 6902 JSON Patch built by a transform; `replace` only) | DELETE (tombstone: GET keeps 200 with `isDeleted`) | Served from `vssps.dev.azure.com`. A create with an existing name returns that group, so it never duplicates. `scopeDescriptor` is a project's descriptor (`scp.…`; by name waits on oasgen-provider#508). Graph reads are eventually consistent; every write the kind makes is idempotent. |
| `GroupMembership` | get by the two descriptors (spec) | none | DELETE (idempotent) | A membership that already exists is adopted by the first get. Subject: a Group's or a user's Graph descriptor. |
| `RepositoryPermission` | get by token + identity descriptor, both **derived** from the spec | POST (replace) | DELETE (idempotent) | A group's entry in the Git security namespace. `permissions` maps the 21 actions to `Allow`/`Deny`/`NotSet`, defaulting to `NotSet`, so a bit set outside the CR is drift. The derivation refuses a missing or malformed component (an error condition, not a wrong request). Users as subjects wait on #508. |
| `FeedPermission` | get by the derived identity descriptor | PATCH (role) | PATCH role `none` | A group's role on a feed. A repeated `none` answers 500 (not idempotent); a stale read can provoke it, and the controller retries until the read converges. |
| `ServiceEndpointUsernamePassword`, `ServiceEndpointToken`, `ServiceEndpointGitHubToken`, `ServiceEndpointServicePrincipal` | findby `name` (`endpointNames`), then get by `status.id` | PUT (full body + `id`) | DELETE from every project in `serviceEndpointProjectReferences` | One kind per authorization scheme (schemes and parameter names measured from `GET _apis/serviceendpoint/types`; GitHub tokens are scheme `Token` with `AccessToken`). The secret parameter is not a spec field: `<parameter>SecretRef {name, key}` names a Secret in the CR's namespace, oasgen-provider grants the controller read access to exactly that Secret, and the reference is never sent. Project references take project GUIDs (a name is a 400). Azure DevOps returns secrets as `null`, so a Secret's value cannot be compared: a rotated Secret reaches Azure DevOps on the next spec change, not by itself. Adopting an existing connection works on 0.57.0 (oasgen-provider#540): the CR finds it by name and corrects it to the spec. |

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
| oasgen-provider#496, #497, #498, #538 | Uninstall (or deleting one RestDefinition) leaves `*Configuration` CRDs, informational notices labelled "generation error:", findby query parameters becoming spec fields (all excluded here). |
| oasgen-provider#505 | `async` paths are plain dot notation (`id`, `status`); a leading dot fails silently after the vendor accepted the call. |
| oasgen-provider#506 | An async update's operation response replaces status; `TeamProject` recovers `status.id` through findby. |
| oasgen-provider#507 | Applying a Configuration restarts the controller; `TeamProject` uses `mode: requeue` so a restart never re-sends a create. |
| oasgen-provider#508 | Dependent lookups cannot send `api-version`: `Queue` needs `spec.pool.id`; Phase 3 identity lookups wait. |
| oasgen-provider#510 | `secretRef` resources failed on 0.53.0 to 0.55.0; 0.56.0 grants each referenced Secret (#527). Still open: revocation waits for the drift poll (measured 48 to 181 s after a delete, healthy CRs). |
| oasgen-provider#537 | A `secretRef` mapping must name its source in `inCustomResource`, or the reference object is sent to the vendor (Azure DevOps answers 400): every ServiceEndpoint kind sets it. |
| oasgen-provider#540 | Fixed in 0.57.0: adopting an existing connection converges (measured 2026-11-11: adopted, corrected, deleted; no duplicate). On 0.56.0 every update of an adopted resource failed. |
| oasgen-provider#486 | No offset pagination (Azure DevOps also needs a short-page signal and cross-page consistency, measured): `Team` is held. |
| oasgen-provider#514 | A bracket-escaped `inQuery` (`'["searchCriteria.sourceRefName"]'`) is not recognised as supplying its parameter at generation: `PullRequest` also excludes the escaped names (runtime binding verified on the wire). |
| oasgen-provider#517, #519 | Identifiers that index into an array (`settings.scope.0.*`) never match at runtime, and generate an object-keyed status: the one-per-branch policy kinds are held. |
| oasgen-provider#518 | A business-rule 403 (e.g. a duplicate policy) is logged as an authorisation denial and the verb is suppressed. |
| oasgen-provider#483 | "identifiers are absent from the items the findby response carries" is a false positive when the fields are inherited through `allOf` (Check, Pipeline, Feed kinds adopt live). |
| oasgen-provider#521 | A verb cannot send a raw (non-JSON) body sourced from a Secret: `SecureFile` waits (Azure DevOps stores the request bytes verbatim, so a JSON body would silently become the file). |
| oasgen-provider#529 | A failed write reported as HTTP 200 with the failure in the body is treated as success: `User` is held. |
| oasgen-provider#567 | Fixed in 0.57.0 (#570): a failed call's error-body snippet is redacted. 0.56.0 logs it unredacted at INFO ([usage](usage.md)). |
| oasgen-provider#566 | Fixed in 0.57.0 (#570): `krateo.io/connector-verbose` response dumps are redacted. |
| oasgen-provider#579, #588 | On 0.57.0: one status-update conflict per RestDefinition after an upgrade, and a controller restart whenever a kind's set of referenced Secrets changes. Harmless here. |
| oasgen-provider#599 | On 0.59.0 a generated controller is never restarted when its ConfigMap changes, so an `rdc.env` change never reaches it: this chart stays on 0.57.0 until the fix ships ([usage](usage.md)). |
| oasgen-provider#528 | Request mappings whose CR path does not resolve are skipped silently; the permission kinds' jq refuses on a missing component instead of composing a wrong token. |
