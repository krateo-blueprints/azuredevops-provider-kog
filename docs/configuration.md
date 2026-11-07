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
      usernameRef: {name: ado-pat, namespace: krateo-system, key: username}
      passwordRef: {name: ado-pat, namespace: krateo-system, key: token}
  configuration:
    query:
      create: {api-version: "7.1"}
      get: {api-version: "7.1"}
```

The exact shape of each kind's Configuration is recorded here as each kind lands. A companion
config chart, which renders all of them from one Secret, comes in Phase 1.
