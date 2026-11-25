---
type: Runbook
title: azuredevops-provider-kog — release
description: How a release ships — one plain-semver tag pushes both charts to GHCR at the same version, then publishes the same bytes to the krateo-blueprints helm index (operators channel). There is no image.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [release, oci, ghcr, chart]
timestamp: 2026-11-07T00:00:00Z
---

# Release

One annotated, plain-semver tag (`X.Y.Z`, no `v`) on `main` releases everything. It triggers
`release-oci.yaml`, which follows the organisation's publishing standard
([krateo-blueprints/charts `PUBLISHING.md`](https://github.com/krateo-blueprints/charts/blob/main/PUBLISHING.md)):
every chart is published twice, with the same bytes (to GHCR and to the helm index), because the
Marketplace installs from the helm index, not from GHCR.

1. **`preflight`** makes the checks specific to this repository, before anything is published. It
   refuses the release if the tagged commit has no successful `lint.yaml` run (which includes
   `oas-assets-fresh` and `render-check`), if either chart does not take both `version` and
   `appVersion` from the tag (`CHART_VERSION`), or if the oasgen-provider pin is on upstream's
   retracted list as read at release time (not only at lint time).
2. **`release-oci`** is one call to the organisation's shared workflow, `release-oci.yaml` 2.1.0,
   pinned by commit SHA (kept current by Dependabot), with `index_channel: operators` (neither
   chart ships a CompositionDefinition) and `CHARTS_PUBLISH_TOKEN`. Before anything is pushed it:
   - refuses a version that is not plain `X.Y.Z` (no `v`, no leading zeros, no pre-release or build
     suffix);
   - checks the index token is present and well formed;
   - refuses to replace a published version whose contents differ, and skips one whose contents
     are identical;
   - passes each chart through the index's own content gate (channel, complete archive, `sources`,
     plain version).

   It then stamps `CHART_VERSION`, packages `chart/` and `config-chart/`, and pushes both to
   `oci://ghcr.io/krateo-blueprints/charts`. Next it pulls back both charts of the release, so the
   index gets the bytes GHCR holds, and publishes them through the organisation's publisher,
   `publish-chart`. That succeeds only once
   `https://krateo-blueprints.github.io/charts/operators/index.yaml` lists both charts and each
   installs anonymously. A chart already published with identical contents is skipped at the push
   but still sent to the index, so if a run pushed and then failed to index, re-running the release
   for the same tag finishes it (2.1.0; on 2.0.0 the re-run showed green and left the index
   without it).

**Rehearsal:** a manual run of `release-oci.yaml` (`workflow_dispatch`) defaults to `dry_run`. It
runs every check and builds every package, pushes nothing, and uploads the packages as the
`release-oci-charts` artifact, so the run shows what it would have published.

`release-notes` writes the GitHub Release body. Tags are never moved or replaced, and a published
version is never overwritten: to fix a release, cut the next version.
