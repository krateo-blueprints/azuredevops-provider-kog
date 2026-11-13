---
type: ExampleIndex
title: azuredevops-provider-kog — examples
description: Index of the runnable examples under examples/.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [krateo, kog, examples]
timestamp: 2026-11-07T00:00:00Z
---

# Examples

- [dev-cluster](../examples/dev-cluster/README.md): a local kind cluster running oasgen-provider
  0.64.0, with the PAT Secret every kind's Configuration references. This is the environment the
  live tests run in.
- [repository-pipeline](../examples/repository-pipeline/README.md): a repository initialized
  with `GitPush`, a YAML `Pipeline` on it, and a `PipelinePermission` on an environment. This is
  the Phase 1 flow, verified live.
