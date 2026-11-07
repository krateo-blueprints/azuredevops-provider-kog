---
type: Usage
title: azuredevops-provider-kog — usage
description: How to install azuredevops-provider-kog on a cluster running oasgen-provider 0.54.1, provide the Azure DevOps PAT, and migrate from the unmigrated classic provider or legacy KOG chart.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [krateo, kog, usage, install, migration]
timestamp: 2026-11-07T00:00:00Z
---

# Usage

## Prerequisites

- Kubernetes **>= 1.36** (required by the oasgen-provider 0.54.1 chart).
- oasgen-provider **0.54.1**: install the `oasgen-provider-crds` chart, then `oasgen-provider`.
  [examples/dev-cluster](../examples/dev-cluster/README.md) has the commands.
- An Azure DevOps PAT in a Secret. The PAT goes in the Configuration's basic-auth `password`.

## Install

```sh
helm install azuredevops-provider-kog oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog \
  --namespace krateo-system
```

No version is published yet. Each RestDefinition must report `READY=True` before its kind is
served:

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
  oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog-config --namespace krateo-system
```

Use a PAT scoped to one organization: global PATs stop working on 2026-12-01.

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
