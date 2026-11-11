---
type: Configuration
title: azuredevops-provider-kog — configuration
description: The azuredevops-provider-kog configuration surface — the chart values resourceGroup and kinds, and the per-kind Configuration (PAT plus api-version).
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [krateo, kog, configuration]
timestamp: 2026-11-07T00:00:00Z
---

# Configuration

## Chart values

| Value | Default | Effect |
|---|---|---|
| `resourceGroup` | `azuredevops.krateo.io` | The API group of every generated CRD. Immutable per RestDefinition once applied. |
| `kinds` | `[]` (all) | Which kinds render. Each one costs a controller pod. Delete a kind's CRs before removing it. |

## Per-kind Configuration

Every kind gets a generated `<Kind>Configuration` (`v1alpha1`) holding the authentication and the
`api-version` for each verb, for example:

```yaml
apiVersion: azuredevops.krateo.io/v1alpha1
kind: GitRepositoryConfiguration
metadata:
  name: ado-config
spec:
  authentication:
    basic:
      usernameRef: {name: azuredevops-pat, namespace: krateo-system, key: username}
      passwordRef: {name: azuredevops-pat, namespace: krateo-system, key: token}
  configuration:
    query:
      create: {api-version: "7.1"}
      get: {api-version: "7.1"}
      findby: {api-version: "7.1"}
      update: {api-version: "7.1"}
      delete: {api-version: "7.1"}
```

## The config chart

`config-chart/` (`azuredevops-provider-kog-config`) renders every kind's Configuration, all with
the same name and all pointing at one Secret, with the right `api-version` for each verb:

| Value | Default | Effect |
|---|---|---|
| `resourceGroup` | `azuredevops.krateo.io` | Must match the provider chart. |
| `configurationName` | `azuredevops` | The name CRs reference in `spec.configurationRef.name`. |
| `secretName` | `azuredevops-pat` | Secret in the release namespace (not created by the chart). |
| `usernameKey` / `tokenKey` | `username` / `token` | Keys in that Secret. The username may be any non-empty value. |
| `kinds` | `[]` (all) | Must not name a kind the provider chart does not render. |

| Kind | Verbs (each gets an `api-version`) | api-version |
|---|---|---|
| `GitRepository` | findby, create, get, update, delete | `7.1` |
| `GitPush` | create, get | `7.1` |
| `Pipeline` | findby, create, get, update, delete | `7.1` |
| `PipelinePermission` | create, get, update | `7.1-preview.1` |
| `TeamProject` | findby, create, get, update, delete | `7.1` |
| `Environment` | findby, create, get, update, delete | `7.1-preview.1` |
| `Queue` | findby, create, get, delete | `7.1` |
| `CheckApproval`, `CheckExclusiveLock`, `CheckRequiredTemplate` | findby, create, get, update, delete | `7.1-preview.1` |
| `CheckTask` | create, get, update, delete | `7.1-preview.1` |
| `PullRequest`, `Feed` | findby, create, get, update, delete | `7.1` |
| `PolicyBuildValidation`, `PolicyRequiredReviewers`, `PolicyStatus` | create, get, update, delete | `7.1` |
| `Run` | create, get | `7.1` |

CI renders this chart and validates every object against the Configuration CRDs that oasgen
actually generates (`hack/render-check.py`). A missing verb, which would send no `api-version`,
fails the build.

## RestDefinition invariants (enforced in CI)

- Every verb's query parameter is either excluded from the spec, bound by a `fieldMapping`, or
  listed with a reason in `hack/render-check-allow.yaml` (`GitRepository.sourceRef`, a fork's create-time input, and `Queue.authorizePipelines`). `excludedSpecFields` is immutable once generated.
- The `kinds` enum in `values.schema.json` equals the kinds the templates guard and render.
- Every `chart/assets/<kind>.yaml` equals what its recipe generates.
