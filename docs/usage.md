---
type: Usage
title: azuredevops-provider-kog — usage
description: How to install azuredevops-provider-kog on a cluster running oasgen-provider 0.84.0, provide the Azure DevOps PAT, know what the controller logs unredacted, and migrate from the unmigrated classic provider or legacy KOG chart.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [krateo, kog, usage, install, migration]
timestamp: 2026-11-07T00:00:00Z
---

# Usage

## Prerequisites

- Kubernetes **>= 1.36** (required by the oasgen-provider 0.84.0 chart).
- oasgen-provider **0.84.0**: install the `oasgen-provider-crds` chart, then `oasgen-provider`.
  [examples/dev-cluster](../examples/dev-cluster/README.md) has the commands.
- An Azure DevOps PAT in a Secret. The PAT goes in the Configuration's basic-auth `password`.

## Install

```sh
helm install azuredevops-provider-kog oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog \
  --version 0.3.0 --namespace krateo-system
```

Both charts are also in the krateo-blueprints helm index (`operators` channel), with the same bytes.
Each RestDefinition must report `READY=True` before its kind is served:

```sh
kubectl get restdefinitions -n krateo-system -o wide
```

Generation warnings appear on each RestDefinition as `status.schemaWarnings` (and in the
oasgen-provider log as `Schema generation warning`). The field is omitted when a render produced
none, so read it together with `status.generatorBuild`: a build at the expected version plus no
`schemaWarnings` means "rendered, no warnings". Two warnings are expected and harmless. One says
a path parameter "is omitted from the generated spec because verb get supplies it"
(oasgen-provider#497 tracks the "generation error:" wording). The other says `Pipeline`'s findby
identifiers "can never match"; that is a false positive, because they arrive via `allOf` and
adoption by name and path works.

Then provide credentials and the Configurations:

```sh
kubectl -n krateo-system create secret generic azuredevops-pat \
  --from-literal=username=kog --from-literal=token="$AZURE_DEVOPS_PAT"
helm install azuredevops-provider-kog-config \
  oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog-config \
  --version 0.3.0 --namespace krateo-system
```

Use a PAT scoped to one organization: global PATs stop working on 2026-12-01.

### What the controller logs

Request bodies are redacted: a value a `secretRef` resolves (the ServiceEndpoint kinds' secret
parameter) never appears in a logged request, and the PAT travels in the `Authorization` header,
which is redacted by name. Since oasgen-provider 0.57.0 (oasgen-provider#570), the two paths that
were not redacted are: the error-body snippet every failed call logs at INFO (#567), and the
response bodies `krateo.io/connector-verbose: "true"` dumps (#566). This chart did not measure
that redaction itself (it needs a failed call that echoes a secret); the source is the upstream
change and its tests. Clusters still on 0.56.0 or earlier log both unredacted.

Keep `connector-verbose` off outside debugging regardless, and give read access to the controller
logs only to those who may read the Secrets.

### Upgrading oasgen-provider to 0.84.0

Upgrade the `oasgen-provider-crds` chart first, then `oasgen-provider`, with a plain
`helm upgrade` (no `--reset-values`, or your `rdc.env` settings are dropped). Both steps were
measured on disposable GKE clusters with this chart's 25 kinds: 0.57.0 to 0.61.0, 0.61.0 to 0.62.0
(2026-11-12), 0.62.0 to 0.63.1 and 0.63.1 to 0.64.0 (2026-11-13), 0.64.0 to 0.65.0 and 0.65.0 to 0.66.0 (2026-11-14), 0.66.0 to 0.68.0, 0.66.0 to 0.69.0 and 0.69.0 to 0.71.0 (2026-11-15), 0.71.0 to 0.72.0 and 0.72.0 to 0.73.0 (2026-11-16), 0.73.0 to 0.74.0 and 0.73.0 to 0.76.0 in one step (2026-11-17), 0.76.0 to 0.84.0 in one step (2026-11-21).
Larger jumps were not run on
their own. What to
expect:

- Every RestDefinition is regenerated (`status.generatorBuild` becomes `0.84.0-de67f828…`) with no
  reconciler error and no provider restart. The status-update conflict 0.57.0 logs once per
  RestDefinition after an upgrade (oasgen-provider#579) is gone.
- **Every generated controller rolls once**, because its image moves to the new
  rest-dynamic-controller. Their ConfigMaps do not change. Live CRs are unaffected: a
  `GitRepository` created before each upgrade stayed Ready with the same id.
- A change to the Secrets a kind's CRs reference no longer restarts its controller
  (oasgen-provider#588): the Deployment revision stays the same.
- An `rdc.env` change on the provider chart (adding or removing a key) rolls every generated
  controller exactly once (oasgen-provider#599, #595). It is eventually consistent: allow up to
  about five minutes, because each RestDefinition picks it up on its own 3-minute poll.
- A CR deleted before its id reaches status (oasgen-provider#593) is no longer orphaned silently.
  When the delete path cannot find the external object, it still releases the CR (holding it
  would make it undeletable), but emits an `OrphanedExternalResourcePossible` Warning Event naming
  the resource. Alert on that reason. `TeamProject` closes the remaining window itself (it lists
  projects with `stateFilter=all`): in the measured trials no project was orphaned at any delay.
- **New in 0.64.0:** the render service chart installed with the provider
  (`controller-render-service`) no longer accepts `resources.limits.memory`. Setting it fails with
  `additional properties 'memory' not allowed`; use `maxBodyMiB` instead (its default gives the same
  512Mi limit). This chart sets neither. 0.64.0's new `Ready=False` handling for kinds that cannot
  create does not apply here: all 25 kinds declare both a create and a get, checked on the live
  RestDefinitions after the upgrade.
- After a create or an update, a CR reports `Ready=False` (`Creating` or `Updating`) until its
  controller's next poll, up to 3 minutes, even though Azure DevOps already has the change
  (oasgen-provider#648, measured on 0.76.0: 3 minutes after an update; not re-measured on 0.84.0). Allow at least that long when waiting for `Ready`.
- **New in 0.65.0: a rotated Secret value now reaches Azure DevOps** (oasgen-provider#598). Before,
  changing the value inside a Secret that a `ServiceEndpoint*` CR references changed nothing at the
  vendor until something else in the CR changed. Now the controller fingerprints the Secrets it
  resolves and issues one update when they change. The four `ServiceEndpoint*` CRDs gain
  `status.resolvedResolversDigest`, and their CRs report a `ResolverDigestRecorded` condition. On
  0.65.0 only, that condition disappears after a CR's first update and does not come back
  (oasgen-provider#668, fixed in 0.66.0 and measured: the condition stays through a rotation's update).
  Measured on Azure DevOps: recording the first digest issues no update; a rotation issues exactly
  one update, which Azure DevOps accepts, and no further one. Azure DevOps never returns secret
  values, so a test cannot read back the stored value itself. No other kind references a Secret.
- If you upgrade with regeneration turned off (`env.OASGEN_PROVIDER_REGENERATE_ON_UPGRADE=false` on
  the provider chart), the old CRDs drop the new status field. Those CRs report
  `ResolverDigestRecorded=False` (`DigestFieldAbsent`) and rotations are not detected, but nothing
  else changes: measured, the controller issued no update at all and wrote the CR once (the
  condition). Turn regeneration back on, or re-apply the RestDefinitions, to get detection.
- **Do not use 0.66.0: upstream retracted it** (oasgen-provider#674: a kind that declares no
  `create` verb writes an annotation about five times a second, forever). This chart is not
  affected, because all 25 kinds declare `create` (checked on the live RestDefinitions), but chart
  0.7.0, which pinned it, is superseded. This repository's CI now refuses a pin on any version
  oasgen-provider lists as retracted.
- **Do not use 0.69.0 or 0.70.0: upstream retracted both** (in favour of 0.71.0) for the
  duplicate described below. Chart 0.8.0, which pinned 0.69.0, is superseded.
- **New in 0.68.0 to 0.71.0:**
  - A create that reached Azure DevOps but whose status write failed is no longer reported as a
    failed create and retried at once (oasgen-provider#676).
  - A kind that declares `get` but has no identifier recorded now reports `Ready=False`
    (`NoIdentifierRecorded`) instead of assuming it is up to date (oasgen-provider#682, #687).
    All 10 kinds here without a `findby` declare `get`, so all 10 are covered. In the live suites
    from 0.71.0 to 0.76.0, and on 0.84.0, no CR reached that state, or the old "assumed up to date"
    one (between 451 and 479 sampled `Ready` conditions per run up to 0.76.0, and 1293 across the
    two 0.84.0 runs, every one with a reason).
- **Fixed in 0.71.0, measured: another writer on the CR during its create no longer duplicates
  the Azure DevOps object** (oasgen-provider#692; fixed by #693 in 0.70.0 and #697 in 0.71.0).
  On 0.69.0, when a second field manager (a GitOps partial apply, or a controller adding labels)
  updated a CR of a kind without a `findby` while it was being created, the status write that
  records the new id could lose, and the controller created again: 5 of 5 forced trials on
  `PolicyStatus` left 2 or 3 policies for one CR. From 0.71.0 to 0.76.0 the same forced race
  fired in 35 of 35 trials (15 on 0.71.0, then 5 each on 0.72.0, 0.73.0, 0.74.0 and 0.76.0) and
  **duplicated in none**: Azure DevOps held exactly one policy per CR every time.
- **New in 0.72.0: `excludedSpecFields` can be edited** (oasgen-provider#666). An edit re-renders
  the CRD on the next poll, so it changes the schema on every live cluster; see
  [configuration](configuration.md) before changing one. This chart's lists are unchanged.
- **New in 0.73.0:** a `Ready=True` that was assumed rather than observed now carries reason
  `AssumedUpToDate` instead of `Available` on the no-`findby` path (oasgen-provider#709). The path
  that assumes because a response had no body still reports `Available` and says so only in its
  message, so match both when you alert. The live suites on 0.73.0 found 0 CRs in either form. The
  paginated `findby` walk was rebuilt (#710); the four kinds here that page (`TeamProject`,
  `Environment`, `Group`, `Pipeline`) passed their live suites, which only exercise a single page.
  A separate run forced one project per page on `TeamProject` (a test-only `$top=1` on its
  `findby`, 6 projects): adopting the project on page 1 cost 1 list request and the one on page 2
  cost 2, so the walk stops on the matching page and keeps its query on later pages. Not measured:
  a walk that finds nothing, and pages beyond 2.
- **Skip oasgen-provider 0.85.0 and 0.85.1; both are retracted upstream, and both create no
  generated controller at all.** Measured here on 0.85.0, an upgrade from 0.76.0: every
  RestDefinition failed with `failed to decode object: yaml: … did not find expected key`, because
  its controller template nests the new `health` port one level too deep. 0.85.1 fixes that, but
  renders `livenessProbe: {}`, which the Kubernetes API server refuses ("must specify a handler
  type"), as measured with a server-side dry run on Kubernetes 1.36. Wait for a release this chart
  pins.
- **Do not set `rdc.metrics.port` on oasgen-provider 0.81.0 to 0.85.1** (oasgen-provider#856). Any
  non-zero value renders a controller template that does not parse, so no controller is created.
  Measured by rendering the 0.84.0 chart with `--set rdc.metrics.port=8080`. At the default of 0 the
  block is not rendered and 0.84.0 works. On 0.80.0 and earlier the chart refuses the value.
- **New in 0.77.0 to 0.84.0 (this chart went from 0.76.0 to 0.84.0 in one step):**
  - **`findby` now refuses two or more matches instead of adopting the first** (oasgen-provider#789,
    from 0.83.0). Measured on `Group` without `spec.scopeDescriptor` (its `findby` then searches
    the whole organization by `displayName`), with two same-named groups in two projects:
    - on 0.76.0, in two runs, the CR adopted one of them (a different one each run) and reported
      `Ready=True`; deleting the CR then **deleted that group**, which it never created;
    - on 0.84.0 the CR stopped at `Ready=Unknown/ObserveFailed` with "findby matched 2 or more
      items on the declared identifiers", and deleting it deleted neither group.

    Up to 0.82.0 the same applies to every kind with a `findby`, whenever more than one Azure
    DevOps object matches its identifiers. **Still open in every version (oasgen-provider#790):**
    the refusal is applied page by page, so two matches on different pages of a paginated list
    are not detected and the first is adopted. That case could not be built here: this
    organization's group list is one page and the endpoint ignores a page size. Give `Group` a
    `spec.scopeDescriptor` so its search stays inside one scope.
  - The Warning Event reason `UnmodelledKeysWouldBeRemoved` is renamed `UnmodelledKeysPresent`
    (0.79.0), and its message no longer predicts that Azure DevOps deletes the keys. Update any
    alert keyed on the old name. Measured on 0.84.0: the same 10 kinds warn under the new name, and
    the old name appears 0 times. The table below still applies.
  - **A kind with no `findby` can be stranded at `CreateOutcomeUnknown` by a refusal outside
    400, 401, 404 and 422.** Measured on 0.84.0 with `GitPush`: a push Azure DevOps rejected with
    409 Conflict (nothing was written) was classified as possibly committed. The kind cannot check
    existence, so the CR stayed at `Ready=False/CreateOutcomeUnknown` for the rest of the run.
    Upstream will stop setting the pending marker on kinds without a `findby` (not yet released);
    **CRs already stranded do not clear by themselves.** Six kinds are exposed: `GitPush`,
    `PolicyStatus`, `PolicyBuildValidation`, `PolicyRequiredReviewers`, `Run` and `CheckTask`. Their
    `get` is addressed by an id that exists only in status, so the existence check falls back to a
    `findby` the kind does not declare (oasgen-provider 0.84.0, `exists.go`). Four other kinds also
    lack a `findby` (`FeedPermission`, `GroupMembership`, `PipelinePermission`,
    `RepositoryPermission`), but their `get` is addressed from the spec, so the check uses it and
    the marker resolves: an absent object or a network failure is an answer there. What to do for
    a stranded CR, depending on what Azure DevOps holds:
    - **The object exists:** write its id into the status field the kind's `get` reads (the remedy
      measured above for `Run`). Do not remove the pending annotation: that sends the create again.
    - **The object does not exist:** remove the annotation, so the controller creates it:
      `kubectl annotate <kind> <name> krateo.io/external-create-pending-`. Upstream measured the
      create then completing; this chart did not.
    - **To remove the CR instead:** a plain `kubectl delete` waits indefinitely, because the delete
      path asks the same unanswerable existence question first. Set the orphan policy first, then
      delete: `kubectl annotate <kind> <name> krateo.io/deletion-policy=orphan`. Anything that
      exists in Azure DevOps is left there. This is upstream's reading of the 0.84.0 runtime, not
      measured here.
  - The provider runs with leader election on by default (0.81.0). The chart's
    `rdc.autoscaling` values are removed (0.84.0), and `serviceAccount.create=false` without a
    `serviceAccount.name` now refuses to render (0.82.0). This chart's install sets none of these.
- **New in 0.74.0:**
  - The controller's request timeout can be set with `rdc.env.REST_CONTROLLER_REQUEST_TIMEOUT`
    (default 30s, oasgen-provider#727).
  - A Warning Event `UnmodelledKeysWouldBeRemoved` reports keys Azure DevOps holds that a CR does not
    express (#725). The live suites on 0.74.0 and 0.76.0 raised 20 of them, on 10 kinds. Nothing
    failed. The warning says an update "would DELETE" those keys, but it cannot know whether a given
    Azure DevOps endpoint deletes an omitted key or keeps it (oasgen-provider#757). This was measured
    against Azure DevOps directly on seven of the kinds. Each author-set key was first set to a non-default value,
    then the object was sent an update shaped like the controller's that left the key out, using the
    chart's own update verb. A field the CR does set was changed in the same update, to prove the
    update applied:

    | Kind | Key the update left out | Result | What to do |
    |---|---|---|---|
    | `PolicyStatus`, `PolicyBuildValidation`, `PolicyRequiredReviewers` | `type.displayName`, `type.url` | kept | ignore |
    | `CheckApproval` | `resource.name` | kept | ignore |
    | `Pipeline` | `repository.name`, `repository.url` | kept | ignore |
    | `PipelinePermission` | `allPipelines.authorizedBy`, `allPipelines.authorizedOn` | kept (both values identical after the update) | ignore |
    | `PolicyRequiredReviewers` | `settings.creatorVoteCounts` | kept (`true` stayed `true`) | ignore |
    | `PolicyBuildValidation` | `settings.manualQueueOnly` | **reset** (`true` became `false`) | set it in the CR |
    | `PolicyRequiredReviewers` | `settings.minimumApproverCount` | **reset** (`2` became `1`) | set it in the CR |
    | `CheckApproval` | `settings.blockedApprovers` | **reset** (one approver became none) | set it in the CR |
    | `Pipeline` | `repository.checkoutSubmodules` | **reset** (`true` became `false`) | set it in the CR |
    | `Pipeline` | `repository.clean` | **reset** (`"true"` became unset) | set it in the CR |
    | `ServiceEndpointServicePrincipal` | `data.identityType` | not removed (`AppRegistrationManual` stayed). Azure DevOps assigns this value, so it could not be set to a non-default first: a reset to its default would look the same | probably ignore; not proven safe |

    So every key Azure DevOps fills in itself was kept, and five of the six settings an author would
    set were reset to their defaults (`creatorVoteCounts` was the exception, so there is no rule that
    predicts which settings survive). A "reset" key matters only if its value was set outside the CR, for
    example in the Azure DevOps UI: the next update the controller sends puts it back to the default.
    Setting the key in the CR avoids that.

    **Not measured:** `CheckExclusiveLock`, `CheckRequiredTemplate` and `CheckTask` warn only on `resource.name`. They use
    the same endpoint as `CheckApproval`, where it was kept, but were not measured themselves.
  - The provider gains a ClusterRole for its status backfill. On an upgrade into 0.74.0 or later its
    first pass can log a short-lived permission Warning per kind. The live runs did not capture
    those events, so they are not counted here.
- **Known issue from 0.71.0, measured through 0.76.0 (the race was not re-run on 0.84.0): a CR that loses that race is left without an
  id and needs a human.** The controller refuses to create again, which is what prevents the duplicate, but it
  cannot find the object it made either: the kind has no `findby` to look it up, and its `get` is
  addressed by the id that was never recorded. The object exists once in Azure DevOps and the CR
  does not reference it. The 35 forced trials ended in one of two states:
  - **33 of 35: `Ready=False` with reason `NoIdentifierRecorded`**, and `Synced=False` whose
    message says the external resource "MAY EXIST and be unreferenced".
  - **2 of 35 (one on 0.71.0, one on 0.73.0): stuck waiting on the create's outcome, indefinitely.**
    `Synced=False` has a message starting `cannot determine creation result - remove the
    krateo.io/external-create-pending annotation if it is safe to proceed`. Up to 0.75.0, `Ready`
    reads `False` with reason `Creating` and no message, so only the `Synced` message tells it
    apart from an ordinary create. From 0.76.0 it has its own reason, `Ready=False` with
    `CreateOutcomeUnknown` (unstructured-runtime#93): a CR put into this state by hand on 0.76.0
    showed that reason.
  - **Do not delete the CR** to clear either state, because that orphans the object. **Do not
    remove the annotation by hand** either, despite what that message says.
  - **Remedy, for both states: write the object's id into the field the kind's `get` reads.**
    Find the object in Azure DevOps, then, for example:
    `kubectl patch policystatus <name> --subresource=status --type=merge -p '{"status":{"id":<id>}}'`.
    `status.id` is an integer, so do not quote it. Write only that one field; the next observe
    reads the object and fills in the rest. **Measured on 0.72.0** (2026-11-16, `PolicyStatus`):
    3 CRs in the `NoIdentifierRecorded` state, and 1 put into the stuck state by hand, each reached
    `Ready=True` within one poll (about 3 minutes) with the same id. Azure DevOps still held one
    policy per CR, and nothing created another. For the stuck CR the runtime set the
    create-succeeded annotation again itself, so the annotation never needs touching. An untouched
    control CR stayed `NoIdentifierRecorded` over the same window. **Measured again on 0.73.0,
    0.74.0 and 0.76.0**, including on a CR that reached the stuck state by itself in the race (on
    0.73.0): every patched CR converged with no new create, and the control held each time.
  - **Exposure: 6 kinds**, those whose `get` is addressed by a field the create response fills in:
    `status.id` on `PolicyStatus`, `PolicyBuildValidation`, `PolicyRequiredReviewers`, `CheckTask`
    and `Run`, and `status.pushId` on `GitPush`. The other 4 kinds without a `findby`
    (`FeedPermission`, `GroupMembership`, `PipelinePermission`, `RepositoryPermission`) build their
    `get` from `spec`, so they are always addressable and cannot reach this state (the RestDefinitions
    here, with oasgen-provider's reading of the source). The race was forced on `PolicyStatus` only.
  - **Avoid it:** do not let other field managers touch CRs of those 6 kinds until they report an
    id in `status`.
  - **Detect it:** a Warning Event with reason `ResourceCreated` whose message says the status
    "could not be written" marks every CR that lost the race. Then look for either state above.
- **Fixed in 0.76.0, measured: a create whose response is lost is no longer sent again**
  (oasgen-provider#747). Up to 0.75.0, if Azure DevOps committed a create but the response never
  reached the controller (a network failure, or a request slower than its timeout), the controller
  recorded the create as failed and sent the same POST again. On kinds where Azure DevOps accepts an
  identical create (`Run`, `PolicyStatus`, `CheckTask`, measured), that left extra objects, and the CR
  tracked only the last.
  - **Measured on `Run`** (2026-11-16 and, for 0.84.0, 2026-11-21; disposable GKE clusters). The controller's request timeout was
    set to the median POST latency, so roughly half the creates were cut:

    | oasgen-provider | Trials where a POST timed out | Re-sent | Runs for one CR |
    |---|---|---|---|
    | 0.74.0 | 4 | 3 | 2, 3, 2 |
    | 0.75.0 | 2 | 2 | 2, 2 (0.75.0's fix did not take effect, oasgen-provider#746) |
    | 0.76.0 | 1 | 0 | 1 |
    | 0.84.0 | 6 | 0 | 1, 1, 1, 1, 1, 1 |

    Controls: a trial at the default timeout, and every trial whose POST did not time out, left exactly
    one run. 0.73.0 has the same create path as 0.74.0 and was not measured separately.
  - **What happens instead from 0.76.0 (measured on 0.76.0 and 0.84.0), for a kind with no `findby`:** the controller cannot check
    whether the create landed, so it stops and waits. The CR shows `Ready=False` with reason
    `CreateOutcomeUnknown`, carries only the `krateo.io/external-create-pending` annotation, and its
    `Synced` message says `cannot determine creation result … this kind declares no findby verb`. The
    object exists once in Azure DevOps. Exposed: the same 6 kinds as the race above, whose `get`
    reads `status.id` or `status.pushId`.
  - **Remedy, measured on 0.76.0 (1 CR) and 0.84.0 (6 of 6 CRs, each `Ready=True` about 3 minutes later with no new run):** find the object in Azure DevOps, write its id into the field the
    `get` reads, and wait one poll. For example:
    `kubectl patch runs.azuredevops.krateo.io <name> --subresource=status --type=merge -p '{"status":{"id":<id>}}'`.
    The patch must use `--subresource=status`; without it the API server accepts the patch and drops
    the status. On the measured CR, `Ready=True` followed about 3 minutes later with the same id. The
    controller added `external-create-succeeded` itself, and no new run was created. One CR on 0.76.0
    and six on 0.84.0; the vendor's run ids were checked each time.
  - **When the object exists, do not remove the `krateo.io/external-create-pending` annotation**,
    whatever the `Synced` message suggests. On 0.76.0, removing it alone made the controller create again in the same
    second, and the existing object was left untracked. This was measured by github-provider-kog on
    GitHub (krateo-blueprints/github-provider-kog#95), not on this chart.
  - **Skip 0.77.0.** On 0.77.0 only, a kind *with* a `findby` whose create did not land (its list
    matches nothing) reports `Creating` indefinitely, with nothing that points a person at it
    (oasgen-provider#758, reverted by #759 for 0.78.0). 15 of this chart's 25 kinds have a `findby`.
    On 0.76.0, which this release pins, that case reports `CreateOutcomeUnknown` instead. This is
    oasgen-provider's reading of its source; it was not measured on this chart.
  - **Still on 0.73.0 to 0.75.0?** The duplicate shows as a CR carrying both
    `external-create-failed` and `external-create-succeeded`, with a Warning Event
    `CannotCreateExternalResource` whose message contains `making request:`. Remove the extra objects
    in Azure DevOps; the CR keeps tracking the one in its `status.id`. From 0.76.0 that annotation
    pair no longer appears, because a lost response is no longer recorded as a failed create.

Do not stop at **0.59.0**: there, an `rdc.env` change never reaches a running controller
(oasgen-provider#599, fixed in 0.60.0). Moving back to an earlier version was not tested; treat
each upgrade as forward only.

**Stale generated CRD (fixed in 0.63.1).** Up to 0.63.0, the provider can keep serving an
outdated generated CRD. This happens when a RestDefinition's OpenAPI document changes and the
provider first sees the change while that kind's controller Deployment is absent. The provider
recreates the Deployment and records the new document hash in `status`, but does not re-render the
CRD. The status then looks healthy, so only comparing the served CRD with the document reveals it.
Measured 2026-11-13 on a disposable GKE cluster, by deleting a kind's controller Deployment and
adding a property to its document within one provider poll:

- **0.62.0:** both test kinds kept their old CRD, and a third poll did not fix it. A kind edited
  with its Deployment present picked the property up.
- **Repair on 0.62.0:** with the controller Deployment Ready,
  `kubectl -n krateo-system patch restdefinition <name> --subresource=status --type=merge -p '{"status":{"oasHash":""}}'`
  re-rendered the CRD in 17 s. Run it only while the Deployment exists. According to
  oasgen-provider, patching while it is absent forms the stale state again; this chart has not
  tested that.
- **An upgrade to a new provider version clears it.** Every definition is re-rendered once (on by
  default since 0.53.0). The stale kind regenerated during the upgrade to 0.63.1 with no patch.
  This corrects the 0.3.0 release notes, which said an upgrade does not clear it, as upstream had
  first stated. A restart at the same version does not re-render.
- **0.63.1:** the same sequence left no stale CRD.

0.63.0 changes nothing about `not`. It moved the CRD generator to a version that could emit richer
`not` subschemas, but a `not` in an OpenAPI document never reaches the generator through a
RestDefinition (oasgen-provider#396), so no document is affected. This was measured by
github-provider-kog against the released binaries. An earlier version of this page said 0.63.0
"starts enforcing" such constraints; that repeated oasgen-provider's 0.63.0 release note, corrected
in oasgen-provider#639.

### Upgrading oasgen-provider from 0.56.0 to 0.57.0

CRDs chart first, then the provider. **Forward only:** a CR reconciled by 0.57.0 is not supported
by 0.56.0 again (oasgen-provider#544 changes how custom-resource paths are read, #545 removes the
per-resource Secret Role). Then continue to 0.76.0 as above.

## Migrating from the classic provider

Both use `azuredevops.krateo.io` and several of the same plural names, so they **cannot run side
by side**. The path, documented in full in Phase 5, is: orphan the classic CRs so nothing is
deleted in Azure DevOps, uninstall the classic provider and its CRDs, install this chart, then
re-apply equivalent CRs. On the first reconcile, `findby` adopts the existing resources.

## Migrating from the legacy KOG chart

That chart used group `azuredevops.ogen.krateo.io`, so it can coexist with this one. Move CRs
across, then uninstall it. If the cluster still runs an oasgen-provider older than 0.20.0, follow
oasgen-provider's `docs/migrating-from-pre-0.20.md` **before** anything else. Getting the
CRD-chart split in the wrong order deletes every RestDefinition and generated CR.
