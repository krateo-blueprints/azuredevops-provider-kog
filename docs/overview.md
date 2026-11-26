---
type: Architecture
title: azuredevops-provider-kog — overview
description: How azuredevops-provider-kog works — RestDefinitions plus trimmed Azure DevOps OpenAPI documents that oasgen-provider 0.96.0 turns into azuredevops.krateo.io CRDs and one controller per kind — and the design decisions and phase plan behind it.
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
| oasgen-provider | `krateo-platformops/oasgen-provider` **0.96.0**, which pins the provider and rest-dynamic-controller together | The only maintained line. Since 0.35.0 both components share one version, so there is no separate controller floor. |
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
| planned | `VariableGroup` | Secret variables are a map keyed by user-chosen names, and a `secretRef` addresses one path: needs a map-valued resolver or a wildcard path (to be designed with oasgen-provider) (oasgen-provider#647) |
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
| oasgen-provider#540 | Fixed in 0.57.0: adopting an existing connection converges (measured 2026-11-11: adopted, corrected, deleted; no duplicate; on 0.61.0 2026-11-12 also `Synced=True` after the correction). On 0.56.0 every update of an adopted resource failed. |
| oasgen-provider#486 | No offset pagination (Azure DevOps also needs a short-page signal and cross-page consistency, measured): `Team` is held. |
| oasgen-provider#514 | A bracket-escaped `inQuery` (`'["searchCriteria.sourceRefName"]'`) is not recognised as supplying its parameter at generation: `PullRequest` also excludes the escaped names (runtime binding verified on the wire). |
| oasgen-provider#517, #519 | Identifiers that index into an array (`settings.scope.0.*`) never match at runtime, and generate an object-keyed status: the one-per-branch policy kinds are held. |
| oasgen-provider#518 | A business-rule 403 (e.g. a duplicate policy) is logged as an authorisation denial and the verb is suppressed. |
| oasgen-provider#483 | "identifiers are absent from the items the findby response carries" is a false positive when the fields are inherited through `allOf` (Check, Pipeline, Feed kinds adopt live). |
| oasgen-provider#521 | A verb cannot send a raw (non-JSON) body sourced from a Secret: `SecureFile` waits (Azure DevOps stores the request bytes verbatim, so a JSON body would silently become the file). |
| oasgen-provider#529 | A failed write reported as HTTP 200 with the failure in the body is treated as success: `User` is held. |
| oasgen-provider#647 | A `secretRef` resolves one path, so a map of secret values is inexpressible: `VariableGroup` waits on a whole-map resolver. Measured on Azure DevOps: a secret's value is never returned, an update that sends it as `null` or omits it keeps the stored value, and a variable left out of the map is deleted. |
| oasgen-provider#674 | 0.66.0 is retracted upstream: a kind with no `create` verb writes an annotation about five times a second, forever. Not reachable here, because all 25 kinds declare `create` (live RestDefinitions, run 066). Chart 0.7.0 pinned 0.66.0 and is superseded. CI (`retracted-pin`) now refuses any pin listed in oasgen-provider's `retracted-versions.yaml`. |
| oasgen-provider#676 | Fixed in 0.68.0: a create that reached the vendor but lost its status write was reported as failed and retried. Measured with an identical POST sent twice: Azure DevOps accepts a duplicate `PolicyStatus`, `CheckTask` and `Run` (the 10 kinds without a `findby` are the exposed ones), and refuses one for `GitRepository` and `ServiceEndpointToken` (409 on the name). |
| oasgen-provider#692 | **Fixed in 0.71.0 (#693 in 0.70.0, #697 in 0.71.0), measured.** On 0.69.0 a second field manager writing a CR while it was created made the status write lose, and the controller created again: in 5 of 5 forced trials on `PolicyStatus` (no `findby`), Azure DevOps ended with 2 or 3 policies for one CR, the CR reported `Ready=True`, and deleting it orphaned the rest. 0.69.0 and 0.70.0 are retracted upstream for it; chart 0.8.0 pinned 0.69.0 and is superseded. On 0.71.0 to 0.76.0 the same race fired in 35 of 35 trials and duplicated in none (one policy per CR every time). **Remaining, measured:** a CR that loses the race is left with no id and needs a human. 33 of 35 reported `Ready=False`/`NoIdentifierRecorded`, and 2 of 35 sat at a bare `Ready=False`/`Creating` with the cause only in `Synced` (unstructured-runtime#93; its `CreateOutcomeUnknown` reason is in no oasgen-provider release yet). Exposed: the 6 kinds whose `get` reads `status.id` or `status.pushId`. The remedy, writing that field, was measured on 0.72.0 and 0.73.0: 8 of 8 CRs converged with no new create (one of them stuck by itself), and an untouched control did not. See [usage](usage.md). |
| oasgen-provider#789, #790 | **Fixed in 0.83.0 (#789), measured; #790 open.** Up to 0.82.0, `findby` adopted the first of two or more matching Azure DevOps objects, and deleting the CR deleted it. Measured on `Group` without `spec.scopeDescriptor`: on 0.76.0 the CR adopted one of two same-named groups and its delete removed that group; on 0.84.0 the CR refused (`Ready=Unknown/ObserveFailed`) and nothing was deleted. #790: two matches on different pages of a paginated list are still adopted in every version. Not constructible here (one page of groups, page size ignored). |
| oasgen-provider#846, #877 | **Works from 0.87.0, measured.** `Ready` reason `CreateRefusedPersistently` for a create Azure DevOps keeps refusing (400, 401, 404 or 422) for over an hour. On 0.85.0 to 0.86.0 the runtime rewrote `Ready` after the failed create and the reason never appeared (measured on 0.85.2 and 0.86.0, over three hours each). On 0.87.0 it appeared, checked at 188 minutes, with the original `lastTransitionTime` and the last status in its message. On 0.89.0, 0.90.0, 0.91.1 and 0.96.0 a network error during one of a refused create's retries moved the CR to `CreateOutcomeUnknown` instead, where it stayed (oasgen-provider#901). Up to 0.95.0 one failed read restarted the hour (#929, fixed in 0.96.0). Azure DevOps's own explanation is logged by the controller as `vendorResponse`, never put on the CR. |
| oasgen-provider#867, unstructured-runtime#119 | **From 0.86.0, measured.** The six kinds whose `get` needs an id held only in status (`CheckTask`, `GitPush`, `PolicyBuildValidation`, `PolicyRequiredReviewers`, `PolicyStatus`, `Run`) carry `ExistenceAnswerable=False` on their RestDefinition, and no other kind does. A CR of those kinds stranded at `CreateOutcomeUnknown` is released by a plain delete (1 s on 0.86.0; on 0.84.0 the delete waits until `krateo.io/deletion-policy=orphan` is set), keeping the Azure DevOps object. |
| oasgen-provider#901 | **Open from 0.76.0 (chart 0.12.0) on, measured on 0.89.0, 0.90.0, 0.91.1 and 0.96.0.** When a create request fails at the network level (no HTTP status), a kind with a `findby` looks the object up; a list that matches nothing is not taken as proof of absence, so the CR stays at `Ready=False/CreateOutcomeUnknown` indefinitely and a delete waits too. 15 kinds are exposed. Removing the `krateo.io/external-create-pending` annotation recovered a CR in that state (constructed by hand) in 12 s on 0.90.0 and 22 s on 0.91.1, and released stuck CRs that were being deleted within 3 s. [Usage](./usage.md#known-issue-a-create-interrupted-by-a-network-error-can-leave-a-cr-stuck) gives how to recognise it and what to do. |
| oasgen-provider#919 | **Open, present in 0.96.0** (its runtime fix, unstructured-runtime#127, is open; 0.96.0 still uses unstructured-runtime v1.32.2). A create refused with 400, 401, 404 or 422 is retried without looking the object up, so a kind whose API accepts a second object can be duplicated (seen on Keycloak). Measured for this chart: sending the same create twice, Azure DevOps kept one object for each of the 15 kinds with a `findby` (14 refuse the second; `Group` returns the existing one). [Usage](./usage.md#known-issue-a-refused-create-is-retried-without-looking-the-object-up) has the table and what was not measured. |
| oasgen-provider#929 | **Fixed in 0.96.0, measured.** Up to 0.95.0 the hour before `CreateRefusedPersistently` was counted from `Ready`'s `lastTransitionTime`, and one failed read of the resource (`Ready=Unknown/ObserveFailed` for a moment) gave it a new one, so the hour started again (measured on 0.91.1 and 0.92.0 by failing one read on purpose; seen unprovoked on 0.92.0 and 0.93.0 after a 503). From 0.96.0 it counts from the `krateo.io/create-refused-since` annotation: the same fault left the reason back 4 s after the failed read, counting from the first refusal. [Usage](./usage.md#fixed-in-0960-one-failed-read-no-longer-restarts-the-hour-before-createrefusedpersistently) has the sequence. |
| oasgen-provider#922, #927 | **Fixed in 0.94.0, measured.** `PolicyBuildValidation`'s `settings.validDuration` is a `number` from 0.92.0; on 0.92.0 and 0.93.0 a fraction (90.5) was read back as `90` and never converged (four updates, then `DriftNotConverging`). From 0.94.0 it is `Ready` with Azure DevOps holding `90.5` and no further update. |
| oasgen-provider#856 | **0.85.0 and 0.85.1 retracted; skip both.** Measured: on 0.85.0 no generated controller renders (the controller template nests the health port one level too deep). On 0.85.1 the template parses but carries `livenessProbe: {}`, which the API server refuses (server-side dry run, Kubernetes 1.36). From 0.81.0 to 0.85.1, a non-zero `rdc.metrics.port` breaks the template the same way (0.84.0 measured by render). |
| oasgen-provider#746, #747 | **Fixed in 0.76.0 (#747), measured.** Up to 0.75.0 a create whose response was lost (network failure, or slower than the controller's request timeout) was sent again without checking whether the first landed. On `Run`, with the timeout set to the median POST latency: 3 of 4 triggered trials on 0.74.0 and 2 of 2 on 0.75.0 left 2 or 3 runs for one CR, the CR tracking only the last (0.75.0's runtime fix did not take effect, #746). On 0.76.0 the one triggered trial left 1 run and the CR stopped at `Ready=False`/`CreateOutcomeUnknown`; writing the run's id into `status.id` brought it to `Ready=True` in about 3 minutes with no new create. Exposed to the stuck state: the 6 kinds whose `get` reads `status.id` or `status.pushId`. See [usage](usage.md). |
| oasgen-provider#682, #687 | 0.69.0: a kind with `get` but no recorded identifier reports `Ready=False`/`NoIdentifierRecorded` instead of "assumed up to date". All 10 kinds without a `findby` declare `get`. The live-suite census on 0.65.0 to 0.76.0 found 0 CRs in either state, with a Ready-reason control on every sample. On 0.69.0 it did not engage under the forced race above; on 0.71.0 to 0.76.0 it is the state 33 of 35 raced CRs ended in. |
| oasgen-provider#648 | After a successful create or update, the next observe waits for the 3-minute poll, so `Ready` lags the vendor by up to one poll interval (measured on 0.64.0, also on earlier releases). |
| oasgen-provider#598 | Fixed in 0.65.0 (measured 2026-11-14): a rotated value in a Secret that a `ServiceEndpoint*` CR references now triggers exactly one update. Recording the first digest issues none, and neither does a CRD generated before 0.65.0 (it reports `ResolverDigestRecorded=False`, `DigestFieldAbsent`). Azure DevOps redacts secrets on read, so what is measured is that the update was sent and accepted, not the stored value. |
| oasgen-provider#668 | On 0.65.0, an update whose response has a body clears the CR's whole `status` before writing it back, and `ResolverDigestRecorded` is only set when a digest is first recorded. So the condition disappears after a CR's first update and stays gone. This was traced in the 0.65.0 source and measured by another consumer on a different vendor. It was not measured on this chart. That this chart is exposed at all rests on an inference: its update PUTs measured 200, and the response body is assumed from Azure DevOps returning the endpoint (not measured separately). Rotation detection is unaffected on the four `ServiceEndpoint*` kinds: their update is synchronous, so the digest is recorded again with the update (measured: no further update after a rotation). Fixed in 0.66.0 (measured 2026-11-14: on 0.66.0 the condition stayed `True` in every captured write across a rotation's update, including the one that set `Ready=False`/`Updating`). |
| oasgen-provider#663 | Not affected (measured on 0.64.0, 0.65.0, 0.66.0, 0.68.0, 0.69.0, 0.71.0, 0.72.0, 0.73.0, 0.74.0 and 0.76.0): the four `ServiceEndpoint*` kinds resolve their secret into the same `authorization.parameters` object their `secretRef` lives in, so that object is never sent empty and the CRs converge. |
| oasgen-provider#567 | Fixed in 0.57.0 (#570): a failed call's error-body snippet is redacted. 0.56.0 logs it unredacted at INFO ([usage](usage.md)). |
| oasgen-provider#566 | Fixed in 0.57.0 (#570): `krateo.io/connector-verbose` response dumps are redacted. |
| oasgen-provider#579, #588 | Fixed (measured on 0.61.0, 0.62.0, 0.63.1, 0.64.0, 0.65.0, 0.66.0, 0.68.0, 0.69.0, 0.71.0, 0.72.0, 0.73.0, 0.74.0 and 0.76.0): no status-update conflict on upgrade, and a change to the Secrets a kind references no longer restarts its controller. On 0.57.0 both happen and are harmless. |
| Stale generated CRD | Fixed in 0.63.1 (measured 2026-11-13): up to 0.63.0, a document change first seen while the kind's controller Deployment is absent leaves the old CRD served, while `status` looks current. An upgrade or the `status.oasHash` reset clears it ([usage](usage.md)). |
| oasgen-provider#593 | Fixed in 0.62.0 (measured 2026-11-12): a CR deleted before its id reaches status no longer orphans silently. The delete path looks the resource up once and, when that finds nothing, releases the CR with an `OrphanedExternalResourcePossible` Warning Event. On 0.61.0 every such delete orphaned the external object with no event. `TeamProject` lists projects with `stateFilter=all`: the default (`wellFormed`) hides a new project for its first seconds, so a delete in that window could not find it (on 0.62.0 with the default, the 0 s trial was still orphaned, with the Warning). With `all`, all four trials deleted the project. |
| oasgen-provider#599 | Fixed in 0.60.0 (measured on 0.61.0, 0.62.0, 0.63.1, 0.64.0, 0.65.0, 0.66.0, 0.68.0, 0.69.0, 0.71.0, 0.72.0, 0.73.0, 0.74.0 and 0.76.0): an `rdc.env` change rolls every generated controller exactly once. On 0.59.0 it never reached a running controller: do not use 0.59.0 ([usage](usage.md)). |
| oasgen-provider#528 | Request mappings whose CR path does not resolve are skipped silently; the permission kinds' jq refuses on a missing component instead of composing a wrong token. |
