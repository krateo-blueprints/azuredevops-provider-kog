---
type: API
title: azuredevops-provider-kog — api
description: The CRDs azuredevops-provider-kog causes oasgen-provider to generate — one resource kind plus a Configuration kind per RestDefinition, under azuredevops.krateo.io.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [krateo, kog, crd, api]
timestamp: 2026-11-07T00:00:00Z
---

# API

> Kubernetes note: use fully qualified resource names with kubectl
> (`gitrepositories.azuredevops.krateo.io`); short names such as `gitrepository` can be ambiguous.

The chart defines no CRDs of its own. For each kind, oasgen-provider 0.55.0 generates:

| Kind | apiVersion |
|---|---|
| `<Kind>` | `azuredevops.krateo.io/<version>`. The version comes from the document's `info.version` (for example `7.1` becomes `v7-1`). |
| `<Kind>Configuration` | `azuredevops.krateo.io/v1alpha1` |

`kubectl get restdefinition <name> -o wide` prints the served version in the `API VERSION` column.
Write CRs against that version, not `v1alpha1`.

## Phase 1 kinds

| Kind | apiVersion | spec | status |
|---|---|---|---|
| `GitRepository` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `name`, `parentRepository` (fork), `sourceRef` (fork) | `id`, `name`, `defaultBranch`, `remoteUrl`, `sshUrl`, `webUrl`, `url` |
| `GitPush` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `repositoryId` (name or id), `refUpdates[]` `{name, oldObjectId}`, `commits[]` `{comment, changes[] {changeType, item.path, newContent {content, contentType}}}` | `pushId`, `date`, `url` |
| `Pipeline` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `name`, `path`, `process {type: 2, yamlFilename}`, `repository {id, type, defaultBranch}` | `id`, `name`, `path`, `revision`, `url`, `queueStatus` |
| `PipelinePermission` | `azuredevops.krateo.io/v7-1-preview` | `organization`, `project`, `resourceType`, `resourceId`, `allPipelines {authorized}`, `pipelines[] {id, authorized}` | `resource` |

Every kind also has `spec.configurationRef` (`{name, namespace}`) and the standard conditions.
`status` fields are append-only once generated.
