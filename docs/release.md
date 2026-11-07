---
type: Runbook
title: azuredevops-provider-kog — release
description: How a release ships — one plain-semver tag drives the shared release-oci workflow, which publishes the chart to ghcr.io/krateo-blueprints/charts. There is no image.
resource: oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog
tags: [release, oci, ghcr, chart]
timestamp: 2026-11-07T00:00:00Z
---

# Release

One annotated, plain-semver tag (`X.Y.Z`, no `v`) on `main` releases everything. `release-oci`
(the shared `krateo-platformops/.github` workflow) substitutes `CHART_VERSION`, packages every
first-class chart and pushes it to `oci://ghcr.io/krateo-blueprints/charts`. It refuses to replace
a published version whose contents differ. `release-notes` writes the GitHub Release body.

Tags are never moved or replaced. To fix a release, cut the next version.
