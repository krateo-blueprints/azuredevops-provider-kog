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

## 2026-11-17 — which `UnmodelledKeysWouldBeRemoved` warnings are real

- Measured against Azure DevOps on four kinds (`PolicyStatus`, `PolicyBuildValidation`,
  `PolicyRequiredReviewers`, `CheckApproval`). Of 9 warned keys, 6 were kept by an update that left
  them out and 3 were reset to their defaults: `manualQueueOnly`, `minimumApproverCount` and
  `blockedApprovers`. Every key Azure DevOps fills in itself (`type.*`, `resource.name`) was kept.
  usage.md now lists which warnings to act on. `Pipeline`, `PipelinePermission` and
  `ServiceEndpointServicePrincipal` are not measured yet.
- Method: each key was set to a non-default value before the update, and the same update changed a
  field the CR does set, to show it applied. Two earlier attempts had harness bugs and are not used:
  one sent the check update with PUT instead of the chart's PATCH, and one used an approver setup
  Azure DevOps rejects (`minimumApproverCount` needs a single group reviewer, TF402457). The first of
  them left two test policies behind. They were deleted, and 0 remain.
- Chart 0.12.0 was released on oasgen-provider 0.76.0. The release-time retracted-version check ran
  for the first time on it and passed.

## 2026-11-17 — oasgen-provider 0.76.0 (a lost create response no longer duplicates)

- Pin moved from 0.73.0 straight to 0.76.0, skipping 0.74.0 and 0.75.0. It was measured on a
  disposable GKE cluster upgrading in place across both in one step, which is the path users of
  chart 0.11.0 take. All 25 RestDefinitions regenerated with the expected stamp
  (`0.76.0-74dbdeba…`), with no reconciler errors. A `GitRepository` created on 0.73.0 kept its id.
  - Live suites: 194/194 checks. 11 of 12 suites passed in run 076. Its smoke-perms results are
    void because the harness lost a helper script mid-suite; the suite was rerun alone on a fresh
    cluster with the same upgrade and passed 17/17.
  - The Ready census found nothing assumed up to date and nothing `NoIdentifierRecorded` outside the
    probe (455 conditions). A Secret-name change restarted no controller; an `rdc.env` add and remove
    rolled all 25 each time. `TeamProject`s deleted 0 to 30 s after creation were all deleted.
  - The forced race fired 5 of 5 with 0 duplicates, 35 of 35 across 0.71.0 to 0.76.0.
- The lost-response arm, unchanged across three releases, shows the fix landing:
  - on 0.74.0, 3 of 4 triggered trials re-sent the create;
  - on 0.75.0, 2 of 2 did (its fix did not reach these controllers);
  - on 0.76.0, the one triggered trial created once and stopped at `CreateOutcomeUnknown`.

  Writing the run's id into `status.id` cleared that CR in about 3 minutes with no new create, which
  was checked against the vendor's run ids. That arm's own verdict line first said otherwise because
  of a counting bug in the harness, since fixed.
- `UnmodelledKeysWouldBeRemoved` (from 0.74.0) raised the same 20 warnings on 10 kinds on 0.74.0 and
  0.76.0, now with full key lists. Upstream has since noted that the warning cannot tell whether an
  endpoint deletes an omitted key, so the docs present it as a prompt to check.
- Skip 0.77.0: oasgen-provider#758 leaves a findby kind whose create did not land reporting
  `Creating` indefinitely. This is upstream's reading, not measured here.
- The harness lost scripts from its working directory a second time (cause still unknown). The suite
  runner now checks each suite's scripts before and after it runs, and marks a suite void if one
  vanished, instead of reporting its failures.

## 2026-11-16 — a lost create response duplicates `Run` (measured); 0.74.0 and 0.75.0 not pinned

- oasgen-provider 0.74.0 passed the full regression here: 194/194 checks, 12 of 12 suites, both
  config arms clean, and the forced race at 0 duplicates (30 of 30 across 0.71.0 to 0.74.0). It was
  not pinned, because 0.75.0 followed the same day.
- A new arm makes a create's response get lost on purpose. It sets the controller's request timeout
  (0.74.0's `REST_CONTROLLER_REQUEST_TIMEOUT`) to the median POST latency measured from inside the
  cluster, then counts runs at Azure DevOps.
  - On 0.74.0, 3 of 4 trials where a POST timed out left 2 or 3 runs for one CR.
  - On 0.75.0, 2 of 2 did, so 0.75.0's fix does not reach these controllers (oasgen-provider#746).
  - The CR tracked only the last run each time. Default-timeout controls left one run.
  - Documented as a known issue for the current release, whose 0.73.0 has the same create path.
    The pin moves when 0.76.0 (#747) is released and measured with the same arm.
- The first design of that arm required a timeout above every GET and below every POST. The vendor's
  latency ranges overlap, so the first run voided before any trial (no data). The bound was stricter
  than needed: a timed-out read cannot cause a create.
- The controller's request counter undercounted where a pod had been replaced: its series carries
  the Deployment name as `service.instance.id`, so a new pod's count overwrote the old one. Runs
  counted at the vendor were the measurement throughout. Reported upstream.

## 2026-11-16 — oasgen-provider 0.73.0

- Pin moved from 0.72.0 to 0.73.0, measured on a disposable GKE cluster upgrading in place from
  0.72.0 with chart 0.10.0. The run waited for all five release artifacts before starting. They
  appeared about 40 minutes after the tag; a check 24 minutes in found none. All 25 RestDefinitions
  regenerated with the expected stamp (`0.73.0-f5f438c5…`), with no reconciler errors. A
  `GitRepository` created on 0.72.0 kept its id.
  - Live suites: 194/194 checks, 12 of 12 suites counted. The five suites that walk a paginated
    `findby` passed, but against this org every walk ends on page 1, so they show no regression in
    0.73.0's rebuilt walk (#710), not that multi-page walks work.
  - The Ready census counts 0.73.0's new `AssumedUpToDate` reason as well as the old message: 452
    sampled conditions, none assumed in either form, none `NoIdentifierRecorded` outside the probe.
    core-provider is not installed on these clusters, so nothing rolled the reason up.
  - A Secret-name change restarted no controller; an `rdc.env` add and remove rolled all 25
    controllers each time. `TeamProject`s deleted 0, 5, 15 and 30 s after creation were all deleted,
    on 0.72.0 and 0.73.0.
- A paging run measured the rebuilt walk on a multi-page `continuationToken` list for the first
  time: `TeamProject` with a test-only `$top=1` (6 projects, page order read twice and stable).
  Adopting the project on page 1 cost exactly 1 list request, and on page 2 exactly 2, counted on
  the controller's request metric for the list path only. So no over-paging after a match, and
  `$top` survived onto page 2. A first attempt produced no data (a harness bug in a count
  comparison) and was rerun.
- The forced race fired in 5 of 5 trials and duplicated in none; 25 of 25 across 0.71.0 to 0.73.0.
  One trial reached the stuck state by itself (its create-succeeded annotation write lost, logged as
  "cannot update managed resource annotations"). Writing its id into `status.id` cleared it with no
  new create, as it did for the three refused CRs and one CR made stuck by hand; the control held.

## 2026-11-16 — oasgen-provider 0.72.0 (remedy for a CR left without an id, measured)

- Pin moved from 0.71.0 to 0.72.0, measured on a disposable GKE cluster upgrading in place from
  0.71.0 with chart 0.9.0. As far as we know this was the first cluster run of 0.72.0 anywhere. All
  25 RestDefinitions regenerated with the expected stamp (`0.72.0-c26413da…`), with no reconciler
  errors and no provider restarts. A `GitRepository` created on 0.71.0 kept its id.
  - Live suites: 194/194 checks, 12 of 12 suites counted.
  - The status-field census filled every declared field on all 25 kinds. The Ready census found no
    CR "assumed up to date" and none `NoIdentifierRecorded` outside the probe (463 sampled Ready
    conditions, all with a reason).
  - `TeamProject`s deleted 0, 5 and 15 s after creation were all deleted, on 0.71.0 and 0.72.0. The
    30 s trial on 0.72.0 does not count: its id was already recorded when the delete was issued.
- The forced race on 0.72.0 fired in 5 of 5 trials and duplicated in none, and all 5 ended
  `NoIdentifierRecorded`. With 0.71.0 that is 20 of 20, 0 duplicates.
- **The remedy for a CR left without an id is now measured**, not only oasgen-provider's reading of
  the source. Writing the vendor id into `status.id` brought 3 refused CRs and 1 CR put into the
  stuck state by hand (by removing only its create-succeeded annotation) to `Ready=True` within one
  poll. The id stayed the same, Azure DevOps still held one policy per CR, and no create followed.
  For the stuck CR the runtime set the create-succeeded annotation again itself. A control CR left
  untouched stayed `NoIdentifierRecorded`.
- **Three harness scripts disappeared from the run's working directory mid-run** (cause unknown).
  Because of that, the `rdc.env` arm printed nothing instead of failing, and the closing digest
  check could not run. The scripts were rebuilt from the session history, the runner now refuses to
  start if a script it calls is missing (tested), and both arms ran again on a second cluster
  upgrading 0.71.0 to 0.72.0. A Secret-name change restarted no controller, and an `rdc.env` add
  and remove rolled all 25 controllers each time.
- `excludedSpecFields` can be edited from 0.72.0 (oasgen-provider#666). Rendered on 0.72.0, 84 of
  this chart's 86 entries change the CRD when removed. The other two, PullRequest's bracket-escaped
  branch filters, change nothing, because the findby binding already keeps them out of the spec. A
  positive control showed that plain entries do silence the "supplied by a fieldMapping" notice,
  and the bracket form does not (filed upstream as oasgen-provider#706). They stay, with their
  comment corrected.
- On 0.72.0, `status.schemaWarnings` already lists routine notices on 23 of 25 RestDefinitions, so
  an alert must match a specific message rather than a non-empty list.

## 2026-11-15 — oasgen-provider 0.71.0 (0.69.0 and 0.70.0 retracted)

- Upstream retracted 0.69.0, which chart 0.8.0 pinned, and 0.70.0, both in favour of 0.71.0, for
  the concurrent-write duplicate this chart measured (oasgen-provider#692). The `retracted-pin` job
  refused the 0.69.0 pin on `main` until this change.
- The forced-race probe on 0.70.0 (before the retraction): the race fired in 3 of 5 `PolicyStatus`
  trials, and all 3 duplicated. The 2 trials where it did not fire stayed clean, which is the
  control. Upstream traced that route to #347's retry branch and fixed it in 0.71.0 (#697).
- Pin moved from 0.69.0 to 0.71.0 (0.70.0 skipped), measured on a disposable GKE cluster upgrading
  in place from 0.69.0 with chart 0.8.0. All 25 RestDefinitions regenerated with the expected stamp
  (`0.71.0-0fb3cbe1…`), with no reconciler errors and no provider restarts. A `GitRepository`
  created on 0.69.0 kept its id.
  - Live suites: 194/194 checks, 12 of 12 suites counted.
  - A Secret-name change restarted no controller; an `rdc.env` add and remove rolled all 25
    controllers each time.
  - `TeamProject`s deleted 0, 5, 15 and 30 s after creation were all deleted, on 0.69.0 and 0.71.0.
  - The status-field census filled every declared field on all 25 kinds. The Ready census found no
    CR "assumed up to date" and none `NoIdentifierRecorded` outside the probe (479 sampled Ready
    conditions, all with a reason).
- The forced race on 0.71.0, in two runs (a probe-only run, then the probe inside the full
  regression): it fired in 15 of 15 trials (one Warning event each) and duplicated in none. Azure
  DevOps held exactly one policy per CR. 14 CRs ended `Ready=False`/`NoIdentifierRecorded`. One
  ended at a bare `Ready=False`/`Creating` with the cause only in `Synced` ("cannot determine
  creation result"): its annotation write had lost a race too. Reported upstream as
  unstructured-runtime#93, now decided as a distinct `Ready` reason (`CreateOutcomeUnknown`) that
  no oasgen-provider release carries yet. Both states need a human, and usage documents them as a
  known issue.
- The full regression on 0.70.0 was invalidated: it ran concurrently with the 0.70.0 probe run, and
  the two collided on fixed fixture names (10 failures in one suite). It was stopped between suites
  and its cluster torn down; 0.70.0 was retracted before it could be rerun. Runs whose suites
  overlap now run one at a time.
- 0.72.0 is published (excludedSpecFields becomes mutable, oasgen-provider#666) and not yet
  measured here. It is next.

## 2026-11-15 — oasgen-provider 0.69.0 (0.66.0 retracted)

- Upstream retracted 0.66.0, which chart 0.7.0 pinned (oasgen-provider#674). The defect needs a
  kind without a `create` verb, and all 25 kinds here declare one, so the chart was not affected.
  The 0.7.0 release notes now say it is superseded.
- CI gained a `retracted-pin` job, `hack/check-retracted.py`. It reads oasgen-provider's
  `retracted-versions.yaml` and refuses a pinned version on that list. An unreadable list fails
  closed (rc 2). Two controls run first: 0.66.0 must be refused with exactly rc 1, and 0.67.0 must
  pass.
- Pin moved from 0.66.0 straight to 0.69.0 (0.68.0 was measured but not pinned), measured on a
  disposable GKE cluster upgrading in place from 0.66.0 with chart 0.7.0. All 25 RestDefinitions
  regenerated with the expected stamp (`0.69.0-31069d35…`), with no reconciler errors and no
  provider restarts. A `GitRepository` created on 0.66.0 kept its id.
  - Live suites: 194/194 checks, 12 of 12 suites counted.
  - A Secret-name change restarted no controller; an `rdc.env` add and remove rolled all 25
    controllers each time.
  - `TeamProject`s deleted 0, 5, 15 and 30 s after creation were all deleted, on 0.66.0 and 0.69.0.
  - The status-field census filled every declared field on all 25 kinds.
  - A new Ready census found no CR "assumed up to date" and none `NoIdentifierRecorded`, on any run
    from 0.65.0 to 0.69.0. Every sampled Ready condition carried a reason, which is its control.
- A new probe measured duplicate risk (oasgen-provider#676) by sending an identical create twice and
  counting objects, with `Run` as the positive control. Azure DevOps accepts a duplicate
  `PolicyStatus`, `CheckTask` and `Run`, and refuses one for `GitRepository` and
  `ServiceEndpointToken` (409 on the name).
- The same probe then forced the trigger: a second field manager wrote the CR during its create, so
  the status write lost. On 0.69.0 this duplicated in 5 of 5 `PolicyStatus` trials (2 or 3 policies
  per CR, the extras orphaned on delete). The trigger was proven by 6 Warning events and 6 log lines.
  #687's refusal never appeared. Reported upstream and documented as a known issue. The first attempt
  of this probe, on 0.68.0, was void: its `PolicyStatus` spec lacked a required field, so the CRs
  never reached the controller.

## 2026-11-14 — oasgen-provider 0.66.0

- Pin moved from 0.65.0 to 0.66.0, measured on a disposable GKE cluster upgrading in place from
  0.65.0 with chart 0.6.0. All 25 RestDefinitions regenerated with the expected stamp
  (`0.66.0-a3e62546…`), with no reconciler errors and no provider restarts. A `GitRepository`
  created on 0.65.0 kept its id. All 25 kinds still declare both a create and a get.
- The 12 live suites ran 194 checks, and all 194 passed in one run. The run now also asserts how
  many suites ran (12 of 12), so a suite can no longer be dropped silently.
- A Secret-name change restarted no controller. Adding and then removing an `rdc.env` key rolled
  all 25 controllers each time. `TeamProject`s deleted 0, 5, 15 and 30 s after creation were all
  deleted at the vendor, before and after the upgrade. The status-field census filled every
  declared field on all 25 kinds over 163 minutes.
- oasgen-provider#668 is fixed in 0.66.0, measured. On 0.65.0, `ResolverDigestRecorded` vanished
  after a CR's first update. On 0.66.0, a dedicated test captured every write during a Secret
  rotation: the condition stayed `True` in all of them, including the one that set
  `Ready=False`/`Updating`. The test also repeated 0.65.0's results:
  - from a pre-0.65.0 CRD: `DigestFieldAbsent` and no update;
  - after regeneration: a rotation sends exactly one update, accepted by Azure DevOps, then none.
- `Ready` returned 3 minutes after the rotation's update (oasgen-provider#648, unchanged).

## 2026-11-14 — oasgen-provider 0.65.0

- Pin moved from 0.64.0 to 0.65.0, measured on disposable GKE clusters upgrading in place from
  0.64.0 with chart 0.5.0. All 25 RestDefinitions regenerated with the expected stamp
  (`0.65.0-c6c27537…`), with no reconciler errors and no provider restarts. A `GitRepository`
  created on 0.64.0 kept its id. All 25 kinds still declare both a create and a get.
- The 12 live suites ran 194 checks, and all 194 passed. Eleven suites ran in one run. The
  `TeamProject` adoption suite was left out of it by mistake, so it ran on its own after the same
  upgrade. It is now in the default suite list.
- A Secret-name change restarted no controller. Adding and then removing an `rdc.env` key rolled
  all 25 controllers each time. `TeamProject`s deleted 0, 5, 15 and 30 s after creation were all
  deleted at the vendor, before and after the upgrade. The status-field census filled every
  declared field on all 25 kinds over 157 minutes.
- New in 0.65.0: a rotated Secret value reaches Azure DevOps (oasgen-provider#598). Exactly the four
  `ServiceEndpoint*` CRDs gained `status.resolvedResolversDigest`; the other 21 kinds reference no
  Secret. This was predicted before the run. A dedicated test on a `ServiceEndpointToken` measured
  outgoing calls with the controller's own request counter:
  - recording the first digest sent no update;
  - a rotation sent exactly one update, which Azure DevOps accepted, then none;
  - with regeneration off, the old CRD reported `DigestFieldAbsent`, sent no update even after a
    rotation, and the CR was written exactly once.
  Azure DevOps never returns secret values, so the stored value itself cannot be read back.
- oasgen-provider#663 (a `secretRef` inside an object the vendor echoes) does not affect this
  chart: the four kinds converged after an update on 0.64.0 and 0.65.0, because the resolved secret
  lands in the same object.

## 2026-11-14 — oasgen-provider 0.64.0

- Pin moved from 0.63.1 to 0.64.0, measured on a disposable GKE cluster upgrading in place from
  0.63.1 with chart 0.4.0. All 25 RestDefinitions regenerated with the expected stamp
  (`0.64.0-17803279…`), with no reconciler errors and no provider restarts. A `GitRepository`
  created on 0.63.1 kept its id.
- All 25 kinds declare both a create and a get on the live RestDefinitions, so 0.64.0's new
  handling of kinds that cannot create does not reach this chart. This chart never sets
  `resources.limits.memory`, which the render chart now rejects.
- The 12 live suites ran 194 checks: 193 passed. One Group check failed when `kubectl wait` exited
  with an error after 99 s of its 420 s budget, while the Group was legitimately waiting for its
  controller's next poll. The suites discarded the error output, so the cause is not known. The
  suites now poll instead of using `kubectl wait`, keep the output of a failed check, and print the
  object's conditions and events on a timeout. The Group suite then passed all 13 checks on a fresh
  0.64.0 cluster.
- A Secret-name change restarted no controller. Adding and then removing an `rdc.env` key rolled
  every controller once each time. `TeamProject`s deleted 0, 5, 15 and 30 s after creation were all
  deleted at the vendor, before and after the upgrade.
- A status-field census sampled every CR for 154 minutes: every declared status field was filled on
  at least one CR of each of the 24 kinds observed (`Environment`'s CRs lived 13 s, too short to
  sample). So Azure DevOps sends every field this chart declares (relevant to
  oasgen-provider#642).
- `Ready` lags a successful create or update by up to one 3-minute poll (oasgen-provider#648); the
  census shows it on every kind.
- `VariableGroup`'s design was measured on Azure DevOps, using a self-hosted pipeline agent to read
  the secret values. A secret's value is never returned. An update that sends it as `null` or omits
  the value keeps the stored value, and a variable left out of the map is deleted. Filed as
  oasgen-provider#647 (a whole-map `secretRef` resolver).

## 2026-11-13 — oasgen-provider 0.63.1

- Pin moved from 0.62.0 to 0.63.1, measured on a disposable GKE cluster upgrading in place from
  0.62.0 with chart 0.3.0. All 25 RestDefinitions regenerated with the expected stamp
  (`0.63.1-692a993e…`), with no reconciler errors and no provider restarts. A `GitRepository`
  created on 0.62.0 kept its id.
- 0.63.1 passed all 12 live suites (194 checks), counting the new `TeamProject` adoption test and
  a separate re-run of the policy suite. A Secret-name change restarted no controller. Adding and
  then removing an `rdc.env` key rolled every controller once each time. `TeamProject`s deleted 0,
  5, 15 and 30 s after creation were all deleted at the vendor, before and after the upgrade.
- The first run's policy suite failed 5 checks because a local file holding a fixture id had
  disappeared. The suite now looks the fixture up in Azure DevOps by name.
- The stale-CRD bug fixed in 0.63.1 was reproduced on purpose on 0.62.0 and checked on 0.63.1
  ([usage](usage.md)). The `status.oasHash` repair was run for the first time. An upgrade turned
  out to clear a stale CRD, which corrects the 0.3.0 release notes.

## 2026-11-13 — TeamProject finds projects that are still being created

- `TeamProject`'s findby now sends `stateFilter=all`. Azure DevOps' project list defaults to
  `wellFormed`, which hides a new project (state `new`) for about 3–7 s. A CR deleted in that
  window could not find the project it had just created, so the project was orphaned
  (oasgen-provider#593 announces it on 0.62.0 but cannot avoid it).
- Measured on the vendor by polling the REST API: `all` lists a new project from the first second
  and does not list soft-deleted projects, which only `stateFilter=deleted` returns. So findby
  cannot adopt a project from the recycle bin.
- Measured on 0.62.0 with this as the only change: TeamProjects deleted 0, 5, 15 and 30 s after
  their create were all deleted at the vendor, with no orphan and no warning. With the default
  filter, the 0 s trial had been orphaned.

## 2026-11-13 — oasgen-provider 0.62.0

- Pin moved from 0.61.0 to 0.62.0, measured on a disposable GKE cluster upgrading in place from
  0.61.0. All 25 RestDefinitions regenerated with the expected stamp (`0.62.0-8d6143fc…`), with
  no reconciler errors and no provider restarts. A `GitRepository` created on 0.61.0 kept its id.
  The run passed 178 of 178 checks across 11 live suites. A Secret-name change restarted no
  controller (#588). Adding and then removing an `rdc.env` key rolled every controller once each
  time (#599).
- oasgen-provider#593, a CR deleted inside its create window: one `TeamProject` per trial was
  deleted 0, 5, 15 and 30 s after its create was sent, before `status.id` was set. On 0.61.0 all 4
  orphaned the project with no event. On 0.62.0 the 5, 15 and 30 s trials deleted the project. At
  0 s the project was still orphaned, but the CR now carried an `OrphanedExternalResourcePossible`
  Warning, because Azure DevOps' default project list hides a project for its first seconds.
- The first run was cut off midway when the session driving it exited. Runs now start detached.
  The next run removes what an interrupted suite left in Azure DevOps, matching only the exact
  per-run names.

## 2026-11-12 — oasgen-provider 0.61.0

- Pin moved from 0.57.0 to 0.61.0. It skips 0.59.0 (oasgen-provider#599) and 0.60.0, which was
  superseded by 0.61.0 on the morning its regression was due.
- Measured on a disposable GKE cluster, upgrading in place from 0.57.0, the path a user takes:
  CRDs chart, then the provider. All 25 RestDefinitions regenerated with the expected build
  stamp (`0.61.0-05546c0e…`, worked out before the run), no reconciler errors and no provider
  restarts. A `GitRepository` created on 0.57.0 stayed Ready with the same id, and its later
  delete removed it from Azure DevOps.
- Full regression on 0.61.0: 178 of 178 checks across 11 live suites. The adoption step now also
  asserts `Synced=True` on the adopted connection (oasgen-provider#540).
- Controller restarts: a change to the Secrets a kind references no longer restarts its controller
  (#588; Deployment revision unchanged over 240 s, longer than the provider's poll). Adding and
  then removing an `rdc.env` key changed all 25 controller ConfigMaps and rolled every controller
  exactly once each time (#599, #595).
- The PAT for these runs now comes from GCP Secret Manager through External Secrets Operator and
  Workload Identity, so a run needs no one at the keyboard.

## 2026-11-11 — Not moving to oasgen-provider 0.59.0

- The 0.57.0 entry below says #579 and #588 were planned for 0.59.0. 0.59.0 fixes #579, but its
  #588 change never restarts a generated controller when its ConfigMap changes
  (oasgen-provider#599), so an `rdc.env` change never reaches a running controller.
- Measured on a disposable GKE cluster: adding and then removing `REST_CONTROLLER_DEBUG` changed all
  25 controller ConfigMaps; the Deployment revision stayed at 1 and every pod was still the one
  created at install. A change to the Secrets a kind references alone correctly caused no restart.
- The pin stays at 0.57.0 until the release carrying #599 and #597 passes the same check.

## 2026-11-11 — GitPush and PullRequest take the repository GUID

- `spec.repositoryId` on `GitPush` and `PullRequest` must be the repository's GUID; the CRD refuses
  a name (pattern on the path parameter, carried into the generated CRD on 0.56.0 and 0.57.0).
- Why: the regression renamed a repository that two `GitPush` CRs named. Their next get answered
  404, they read as absent, and each re-sent its create (two `CannotCreateExternalResource` 404s).
  It failed only because nothing held the old name; a repository that did would have received
  the same commits again. A `PullRequest` would be opened in that other repository.
- Breaking for a CR written with a name: set `repositoryId` to `GitRepository` `status.id`.
  The example takes it from there (`REPO_ID`).

## 2026-11-11 — oasgen-provider 0.57.0

- Pin moved from 0.56.0 to 0.57.0. The cluster upgraded in place: CRDs chart first (its
  RestDefinition CRD is byte-identical to 0.56.0's), then the provider. All 25 RestDefinitions
  re-rendered and stamped `0.57.0-cb969ddcecee…`, every controller rolled to
  rest-dynamic-controller 0.57.0, and the live CRs kept identical conditions. The render check
  gives the same 53 warnings on 0.56.0 and 0.57.0.
- Full regression on 0.57.0: 171 of 173 checks across 11 live suites. Both failures were the
  tests, and both reran clean once fixed: a drift check that could pass before the drift reached
  Azure DevOps, and a create check whose wait could fail on a busy control plane.
- Adopting an existing service connection now converges (oasgen-provider#540): smoke-se 50/50.
- Logging: 0.57.0 redacts the error-body snippet and verbose response dumps (#566, #567).
- Found and reported upstream: one status-update conflict per RestDefinition on upgrade
  (oasgen-provider#579) and an unconditional controller restart whenever a kind's set of
  referenced Secrets changes (#588, measured: the ConfigMap and image unchanged, the pod restarted).
  Both are harmless here and planned for 0.59.0.
- Forward only: #544 and #545 make a 0.57.0-reconciled CR unsupported on 0.56.0.

## 2026-11-11 — 0.1.0

- First release: both charts at 0.1.0 in GHCR and the krateo-blueprints helm index (`operators`),
  25 kinds, pinned to oasgen-provider 0.56.0. The index copies are byte-identical to GHCR's.
- Usage now states what the controller logs unredacted on 0.56.0: the error-body snippet of every
  failed call at INFO (oasgen-provider#567) and, under `connector-verbose`, response bodies (#566).

## 2026-11-09 — oasgen-provider 0.56.0 and Phase 2c

- Pin moved from 0.55.0 to 0.56.0. The cluster upgraded in place (CRDs chart first, then the
  provider); `status.secretRefDigest` read back on every RestDefinition, so no new field was pruned.
  The render check gives the same 53 warnings on 0.55.0 and 0.56.0 across all 25 kinds.
- Full regression of the 21 previously shipped kinds on 0.56.0: 123 checks across 10 live suites, no
  failures.
- Four service-connection kinds, one per authorization scheme, live-verified on 0.56.0:
  `ServiceEndpointUsernamePassword`, `ServiceEndpointToken`, `ServiceEndpointGitHubToken` and
  `ServiceEndpointServicePrincipal`. The secret comes from a Kubernetes Secret through a `secretRef`
  resolver; 0.56.0 grants the controller read access to exactly the Secrets the CRs name
  (oasgen-provider#510, #527). Covered: create, no drift across a poll, update, delete, two CRs with two
  Secrets, a connection shared with two projects (deleted from both), and the grant revoked after
  the last CR goes (48 to 181 s, healthy CRs).
- Measured and recorded: schemes and parameter names come from `GET _apis/serviceendpoint/types`
  (there is no PersonalAccessToken scheme: a GitHub token is scheme `Token` with `AccessToken`; `npm`
  does not take `Token`). A `secretRef` mapping must name its source in `inCustomResource`, or the
  reference object is sent and Azure DevOps answers 400 (oasgen-provider#537). Dropping the redacted
  `null` secret from the response emptied `parameters` and read as drift, so no transform drops it.
- Not yet: adopting an existing connection finds it but never converges, because the update
  demands a per-resource Role that only a create makes (oasgen-provider#540, removal decided
  upstream; present since at least 0.52.0).

## 2026-11-09 — Phase 3

- Four more native kinds, live-verified on oasgen-provider 0.55.0: `Group` and `GroupMembership`
  (Graph, `vssps.dev.azure.com`), `RepositoryPermission` (Git security namespace) and
  `FeedPermission`.
- Permissions take user terms: ids, a Group's Graph descriptor and named permissions or a role. The
  security token and the identity descriptor are derived by request jq (measured: the identity
  descriptor is the base64-decoded `vssgp.` descriptor), and the jq refuses a missing or malformed
  component. Every permission defaults to `NotSet`, so a bit set outside the CR is corrected.
- Measured and recorded: group create returns the existing same-named group, update is JSON Patch
  `replace` only (an empty patch is a 500), delete leaves a readable tombstone; Graph reads are
  eventually consistent; a second feed-permission removal answers 500.
- Held: `User` (built, verified for valid principals): a failed add is HTTP 200 with
  `isSuccess: false`, which oasgen cannot surface yet (oasgen-provider#529, filed).
- `trim-oas`: an unkept HEAD operation no longer leaks into an asset, and a `move` patch op
  specialises templated path segments.

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

## 2026-11-08 — Phase 4 (Run)

- `Run`, live-verified on oasgen-provider 0.54.1: a CR triggers one run of a YAML pipeline and
  reports its state and result. Every POST starts a new run, so there is no adoption; a run is
  immutable; deleting the CR releases it and keeps the run, its logs and history.
- `SecureFile` is not shipped: its upload body is the raw file bytes (from a Secret), which a verb
  cannot send today (oasgen-provider#521, measured: Azure DevOps stores the request bytes verbatim,
  so a JSON body would silently become the file), and Secret-backed kinds wait on #510.

## 2026-11-08 — Phase 2b

- Five more native kinds, live-verified on oasgen-provider 0.54.1: `PullRequest` (delete abandons;
  an abandoned PR is absent), `PolicyBuildValidation`, `PolicyRequiredReviewers`, `PolicyStatus`
  (one typed kind per branch-policy type; soft delete via `isDeleted`), and `Feed` (Azure Artifacts,
  on `feeds.dev.azure.com`; soft delete, name stays reserved).
- Measured and recorded in the recipes: one active PR per branch pair, policy uniqueness per type
  (one-per-branch types 403 a second), false flags omitted from reads (normalised), unset policy
  settings returned null (dropped), the `validDuration`/`queueOnSourceUpdateOnly` rule.
- Held: the four one-per-branch policy kinds. Their lifecycle passes, but their identity sits in
  `settings.scope[0]` and index-path identifiers never match on 0.54.1 (oasgen-provider#517, #519);
  a pre-existing policy then wedges the CR on a 403 misread as authorisation (#518).
- Verified on the wire that bracket-escaped `inQuery` bindings are sent (oasgen-provider#514 is
  generation-only).

## 2026-11-07 — Phase 2a

- Seven more native kinds, live-verified on oasgen-provider 0.54.1: `TeamProject` (async
  create/update/delete via operations), `Environment`, `Queue` (pool by id), and one kind per check
  type: `CheckApproval`, `CheckExclusiveLock`, `CheckRequiredTemplate`, `CheckTask`.
- Recipes can `include` an operation from a second archived spec (the projects poll endpoint).
- Measured corrections, each recorded in its recipe: 202 + operation for project writes, 204 deletes,
  list envelopes, the plain list overloads where the archive kept the "by ids/names" ones, the
  missing check `settings` and `version`, lowercased check type ids.
- Held: `Team` (verified; waits on offset pagination, oasgen-provider#486) and the service-connection
  kinds (wait on oasgen-provider#510).
- Upstream issues filed: oasgen-provider #505, #506, #507, #508, #510; measurements posted on #486.

## 2026-11-07 — Publish to the helm index, not only GHCR

The organisation adopted one publishing standard (krateo-blueprints/charts `PUBLISHING.md`): a
chart in GHCR and missing from the helm index is not published, because the Marketplace installs
from the index.

- **Channel `operators`:** neither chart ships a CompositionDefinition.
- **Same bytes:** after the shared `release-oci` push, the release pulls both charts back from
  GHCR and hands those archives to the publisher.
- **Refuse before publishing:** plain-semver tag, a successful `lint.yaml` run on the tagged
  commit, and `CHARTS_PUBLISH_TOKEN` present, all checked before GHCR holds anything.
- **Names are free:** neither `azuredevops-provider-kog` nor `azuredevops-provider-kog-config`
  had an entry in either channel's index.

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
