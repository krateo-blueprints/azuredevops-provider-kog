---
type: API
title: azuredevops-provider-kog — api
description: The CRDs azuredevops-provider-kog causes oasgen-provider to generate — one resource kind plus a Configuration kind per RestDefinition, under azuredevops.krateo.io.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [krateo, kog, crd, api]
timestamp: 2026-11-07T00:00:00Z
---

# API

The chart defines no CRDs of its own. For each kind, oasgen-provider 0.54.0 generates:

| Kind | apiVersion |
|---|---|
| `<Kind>` | `azuredevops.krateo.io/<version>`. The version comes from the document's `info.version` (for example `7.1` becomes `v7-1`). |
| `<Kind>Configuration` | `azuredevops.krateo.io/v1alpha1` |

`kubectl get restdefinition <name> -o wide` prints the served version in the `API VERSION` column.
Write CRs against that version, not `v1alpha1`.

No kind is generated yet (Phase 0). Each kind's spec and status fields are listed here when it lands.
