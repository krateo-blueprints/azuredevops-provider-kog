# azuredevops-provider-kog

## What is this

A Krateo **KOG** provider, built on
[`oasgen-provider`](https://github.com/krateo-platformops/oasgen-provider) **0.57.0**. It exposes
Azure DevOps REST resources (projects, Git repositories, pipelines, permissions, service
connections, variable groups, artifact feeds, teams, groups and users) as Kubernetes kinds under
`azuredevops.krateo.io`. The chart ships RestDefinitions plus trimmed OpenAPI documents only: no
image, no plugin, no proxy.

It replaces the unmigrated classic azuredevops-provider (hand-written controllers) and the legacy
azuredevops KOG chart (oasgen-provider 0.10 plus a proxy plugin).

> **Status: Phase 2c.** Twenty-five kinds (repositories, pushes, pull requests, branch policies, pipelines,
> pipeline runs, permissions, projects, environments, queues, pipeline checks, feeds, groups,
> memberships, repository/feed permissions and service connections) are native and live-verified against Azure DevOps. See [docs/overview.md](docs/overview.md) for
> the per-kind behaviour, the plan and the design decisions.

## Install

Prerequisite: oasgen-provider **0.57.0** on the cluster
([examples/dev-cluster](examples/dev-cluster/README.md)).

```sh
helm install azuredevops-provider-kog oci://ghcr.io/krateo-blueprints/charts/azuredevops-provider-kog \
  --namespace krateo-system
```

This chart is **mutually exclusive** with the classic provider (same API group). See
[docs/usage.md](docs/usage.md) for migration.

## Configure

Two values: `resourceGroup` (default `azuredevops.krateo.io`) and `kinds` (empty renders all).
Each kind's generated `<Kind>Configuration` holds the PAT (basic auth) and the `api-version`;
the companion `config-chart/` renders them all from one Secret.
See [docs/configuration.md](docs/configuration.md).

## Examples

- [examples/dev-cluster](examples/dev-cluster/README.md): local kind cluster with
  oasgen-provider 0.57.0 and the Azure DevOps PAT Secret.
- [examples/repository-pipeline](examples/repository-pipeline/README.md): repository, initial
  push, YAML pipeline and pipeline permission, the flow verified live.

## Docs

- [docs/index.md](docs/index.md): the map
- [docs/overview.md](docs/overview.md): how it works, decisions, phase plan
- [docs/usage.md](docs/usage.md): install and migration
- [docs/configuration.md](docs/configuration.md): the configuration surface
- [docs/api.md](docs/api.md): the generated CRDs
- [docs/examples.md](docs/examples.md): examples index
- [docs/release.md](docs/release.md): how a release ships
- [docs/log.md](docs/log.md): curated history

## Develop & release

OpenAPI documents are generated, never hand-edited: `hack/fetch-specs.py hack/oas-recipes .specs`
then `hack/trim-oas.py .specs hack/oas-recipes/<kind>.yaml chart/assets/<kind>.yaml`. CI checks
freshness and runs `hack/render-check.py` against oasgen-render from the oasgen-provider 0.57.0
image. `helm template` against a substituted copy (the `CHART_VERSION` placeholder fails
`helm lint`). Live tests run on [examples/dev-cluster](examples/dev-cluster/README.md) against a
dedicated, throwaway Azure DevOps organisation. Release: push an annotated `X.Y.Z` tag on `main`
([docs/release.md](docs/release.md)).
