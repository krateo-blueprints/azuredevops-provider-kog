---
type: Usage
title: azuredevops-provider-kog — usage
description: How to install azuredevops-provider-kog on a cluster running oasgen-provider 0.62.0, provide the Azure DevOps PAT, know what the controller logs unredacted, and migrate from the unmigrated classic provider or legacy KOG chart.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [krateo, kog, usage, install, migration]
timestamp: 2026-11-07T00:00:00Z
---

# Usage

## Prerequisites

- Kubernetes **>= 1.36** (required by the oasgen-provider 0.62.0 chart).
- oasgen-provider **0.62.0**: install the `oasgen-provider-crds` chart, then `oasgen-provider`.
  [examples/dev-cluster](../examples/dev-cluster/README.md) has the commands.
- An Azure DevOps PAT in a Secret. The PAT goes in the Configuration's basic-auth `password`.

## Install

```sh
helm install azuredevops-provider-kog oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog \
  --version 0.2.0 --namespace krateo-system
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
  --version 0.2.0 --namespace krateo-system
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

### Upgrading oasgen-provider to 0.62.0

Upgrade the `oasgen-provider-crds` chart first, then `oasgen-provider`, with a plain
`helm upgrade` (no `--reset-values`, or your `rdc.env` settings are dropped). Both steps were
measured on disposable GKE clusters with this chart's 25 kinds: 0.57.0 to 0.61.0 and 0.61.0 to
0.62.0 (2026-11-12). The direct jump from 0.57.0 to 0.62.0 was not run on its own. What to expect:

- Every RestDefinition is regenerated (`status.generatorBuild` becomes `0.62.0-8d6143fc…`) with no
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

Do not stop at **0.59.0**: there, an `rdc.env` change never reaches a running controller
(oasgen-provider#599, fixed in 0.60.0). Moving back to an earlier version was not tested; treat
each upgrade as forward only.

**Stale generated CRD (upstream, fixed in 0.63.1).** According to oasgen-provider, every release
up to 0.63.0 can keep serving an outdated generated CRD when a RestDefinition's OpenAPI document
changes and that change is first observed while the kind's controller Deployment is absent, as
can happen during a provider upgrade or restart. An upgrade does not clear it. This chart has not
observed it. If a kind's CRD does not match its document after an upgrade, follow
oasgen-provider's guidance for 0.63.1.

### Upgrading oasgen-provider from 0.56.0 to 0.57.0

CRDs chart first, then the provider. **Forward only:** a CR reconciled by 0.57.0 is not supported
by 0.56.0 again (oasgen-provider#544 changes how custom-resource paths are read, #545 removes the
per-resource Secret Role). Then continue to 0.62.0 as above.

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
