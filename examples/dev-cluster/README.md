---
type: Example
title: azuredevops-provider-kog — dev-cluster example
description: A local kind cluster running oasgen-provider 0.61.0 plus the Azure DevOps PAT Secret every kind's Configuration references; the environment the live tests run in.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [example, kind, oasgen-provider, dev]
timestamp: 2026-11-07T00:00:00Z
---

# dev-cluster

Use a **dedicated, throwaway Azure DevOps organisation**. The live tests create and delete
projects, groups, users and permissions at organisation scope.

## 1. Cluster and oasgen-provider 0.61.0

Install the CRDs chart first, then the provider. That order is only safe on a fresh cluster; to
upgrade an install older than 0.20.0, read oasgen-provider's `docs/migrating-from-pre-0.20.md` first.

oasgen-provider 0.61.0 requires **Kubernetes >= 1.36** (`kubeVersion: >=1.36.0-0` in its chart),
so pin a 1.36 node image. This one comes from the kind v0.33.0 release, so use kind >= v0.33.0:

```sh
kind create cluster --name ado-kog \
  --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed
helm install oasgen-provider-crds oci://ghcr.io/krateo-platformops/charts/oasgen-provider-crds \
  --version 0.61.0
helm install oasgen-provider oci://ghcr.io/krateo-platformops/charts/oasgen-provider \
  --version 0.61.0 --namespace krateo-system --create-namespace
kubectl -n krateo-system rollout status deploy/oasgen-provider --timeout=180s
```

## 2. The PAT Secret

```sh
kubectl -n krateo-system create secret generic ado-pat \
  --from-literal=username=kog \
  --from-literal=token="$AZURE_DEVOPS_PAT"
```

The username can be any non-empty value; Azure DevOps authenticates on the PAT in `password`.

## 3. The chart

`chart/Chart.yaml` carries the `CHART_VERSION` placeholder, which release-oci substitutes. Helm
refuses that placeholder, so install from a substituted copy:

```sh
TMP=$(mktemp -d) && cp -R chart "$TMP/" \
  && sed -i.bak 's/^version: CHART_VERSION$/version: 0.0.0-dev/' "$TMP/chart/Chart.yaml"
helm install azuredevops-provider-kog "$TMP/chart" --namespace krateo-system
kubectl get restdefinitions -n krateo-system -o wide
```

## Teardown

```sh
kind delete cluster --name ado-kog
```
