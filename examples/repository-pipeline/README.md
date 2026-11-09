---
type: Example
title: azuredevops-provider-kog — repository-pipeline example
description: A Git repository initialized with a native GitPush, a YAML pipeline on it, and pipeline access to an environment, applied as azuredevops.krateo.io CRs; the Phase 1 flow verified live against Azure DevOps.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [example, git, pipeline, azure-devops]
timestamp: 2026-11-07T00:00:00Z
---

# repository-pipeline

The flow Phase 1 was verified with, against a live organisation:
`GitRepository` → `GitPush` (initial commit) → `GitPush` (pipeline file) → `Pipeline`, plus a
`PipelinePermission` on an environment.

Prerequisites: [dev-cluster](../dev-cluster/README.md) (oasgen-provider 0.56.0, the chart and
its RestDefinitions Ready), the config chart installed with `configurationName: azuredevops`, an
existing project, and an existing environment for the last step.

Set `ORG`, `PROJECT` and, for the last step, `ENV_ID`; then apply the files in order. Replace
`<repository-id>` with `status.id` of the repository, and `<main-head>` with the `objectId` of
`refs/heads/main` after the first push.

```sh
envsubst < 1-repository.yaml | kubectl apply -f -
kubectl -n krateo-system wait gitrepositories.azuredevops.krateo.io/example-repo --for=jsonpath='{.status.id}'
envsubst < 2-initial-push.yaml | kubectl apply -f -
# after the initial push: GitRepository status.defaultBranch becomes refs/heads/main
envsubst < 3-pipeline-file.yaml | kubectl apply -f -    # needs <main-head>
envsubst < 4-pipeline.yaml | kubectl apply -f -         # needs <repository-id>
envsubst < 5-pipeline-permission.yaml | kubectl apply -f -
```

Use the fully qualified resource names (`gitrepositories.azuredevops.krateo.io`, …): short names
such as `gitrepository` can be ambiguous to kubectl.

## Deleting

- `GitRepository`: the repository goes to the project's **recycle bin** (Azure DevOps's soft
  delete). The name is reusable immediately.
- `Pipeline`: the definition is deleted.
- `GitPush`: deleting the CR only releases it. A push is history and cannot be undone.
- `PipelinePermission`: deleting the CR **leaves the grants in place** (no delete verb until
  oasgen-provider#502). To revoke, set `authorized: false`, let it reconcile, then delete the CR.
