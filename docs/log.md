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

## 2026-11-07 — Phase 0

- Repository scaffolded on the github-provider-kog layout.
- Decisions: oasgen-provider 0.54.0; group `azuredevops.krateo.io` (mutually exclusive with the
  classic provider); singular kind names; native `dependentLookups` for name→id resolution; a
  dedicated `GitPush` kind for repository initialisation; `Pipeline` on `build/definitions`;
  no plugin.
- Filed oasgen-provider #490 (a delete is sent without a lookup-supplied query parameter). It
  blocks the permission kinds' delete verb.
