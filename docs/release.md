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
every chart is published twice, with the same bytes, because the Marketplace installs from the
helm index, not from GHCR.

1. **`preflight`** refuses the release before anything is published if the tag is not plain
   semver, if the tagged commit has no successful `lint.yaml` run (which includes
   `oas-assets-fresh` and `render-check`), or if `CHARTS_PUBLISH_TOKEN` is not configured.
2. **`release-oci`** (the org's shared workflow) stamps `CHART_VERSION` (both `version` and `appVersion`), discovers `chart/` and
   `config-chart/`, packages both and pushes them to `oci://ghcr.io/krateo-blueprints/charts`.
   It refuses to replace a published version whose contents differ, and skips one whose contents
   are identical.
3. **`collect`** pulls both charts back from GHCR and uploads them as the `charts-dist` artifact.
   That guarantees the index gets exactly the bytes GHCR holds (`helm package` writes fresh
   timestamps, and a skipped push means the local archive was never published). It asserts the
   artifact holds exactly the two charts, each with `version` and `appVersion` equal to the tag.
4. **`publish-index`** calls the organisation's publisher, `publish-chart.yaml`, pinned by commit
   SHA (kept current by Dependabot), with `channel: operators`: neither chart ships a
   CompositionDefinition. The publisher stores the archives, merges the index, and succeeds only
   once `https://krateo-blueprints.github.io/charts/operators/index.yaml` lists both charts and
   each installs anonymously.

`release-notes` writes the GitHub Release body. Tags are never moved or replaced, and a published
version is never overwritten: to fix a release, cut the next version.
