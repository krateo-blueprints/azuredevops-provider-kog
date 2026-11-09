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

## Kinds

| Kind | apiVersion | spec | status |
|---|---|---|---|
| `GitRepository` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `name`, `parentRepository` (fork), `sourceRef` (fork) | `id`, `name`, `defaultBranch`, `remoteUrl`, `sshUrl`, `webUrl`, `url` |
| `GitPush` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `repositoryId` (name or id), `refUpdates[]` `{name, oldObjectId}`, `commits[]` `{comment, changes[] {changeType, item.path, newContent {content, contentType}}}` | `pushId`, `date`, `url` |
| `Pipeline` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `name`, `path`, `process {type: 2, yamlFilename}`, `repository {id, type, defaultBranch}` | `id`, `name`, `path`, `revision`, `url`, `queueStatus` |
| `PipelinePermission` | `azuredevops.krateo.io/v7-1-preview` | `organization`, `project`, `resourceType`, `resourceId`, `allPipelines {authorized}`, `pipelines[] {id, authorized}` | `resource` |
| `TeamProject` | `azuredevops.krateo.io/v7-1` | `organization`, `name`, `description`, `visibility`, `capabilities {versioncontrol.sourceControlType, processTemplate.templateTypeId}` | `id`, `name`, `state`, `revision`, `url`, `visibility` |
| `Environment` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `name`, `description` | `id`, `name`, `createdOn`, `lastModifiedOn` |
| `Queue` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `name`, `pool {id, name}`, `authorizePipelines` | `id`, `name`, `projectId`, `pool.id` |
| `CheckApproval` | `azuredevops.krateo.io/v7-1-preview` | `organization`, `project`, `type` (defaulted), `resource {type, id}`, `timeout`, `settings {approvers[].id, minRequiredApprovers, instructions, executionOrder, requesterCannotBeApprover, blockedApprovers[].id}` | `id`, `version`, `type`, `resource` |
| `CheckExclusiveLock` | `azuredevops.krateo.io/v7-1-preview` | `organization`, `project`, `type` (defaulted), `resource {type, id}`, `timeout` | `id`, `version`, `type`, `resource` |
| `CheckRequiredTemplate` | `azuredevops.krateo.io/v7-1-preview` | as above, plus `settings.extendsChecks[] {repositoryType, repositoryName, repositoryRef, templatePath}` | `id`, `version`, `type`, `resource` |
| `CheckTask` | `azuredevops.krateo.io/v7-1-preview` | as above, plus `settings {definitionRef {id, name, version}, displayName, inputs, retryInterval, linkedVariableGroup}` | `id`, `version` |
| `PullRequest` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `repositoryId` (name or id), `sourceRefName`, `targetRefName`, `title`, `description`, `isDraft` | `pullRequestId`, `status`, `url`, `creationDate` |
| `PolicyBuildValidation` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `isEnabled`, `isBlocking`, `type` (defaulted), `settings {buildDefinitionId, displayName, queueOnSourceUpdateOnly, manualQueueOnly, validDuration, filenamePatterns[], scope[] {repositoryId, refName, matchKind}}` | `id`, `revision` |
| `PolicyRequiredReviewers` | `azuredevops.krateo.io/v7-1` | as above, with `settings {requiredReviewerIds[], minimumApproverCount, creatorVoteCounts, message, filenamePatterns[], scope[]}` | `id`, `revision` |
| `PolicyStatus` | `azuredevops.krateo.io/v7-1` | as above, with `settings {statusName, statusGenre, invalidateOnSourceUpdate, authorId, defaultDisplayName, policyApplicability, filenamePatterns[], scope[]}` | `id`, `revision` |
| `Feed` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `name`, `description`, `badgesEnabled`, `hideDeletedPackageVersions` | `id`, `url` |
| `Run` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `pipelineId`, `resources.repositories.<name> {refName, version}`, `templateParameters`, `stagesToSkip[]` | `id`, `name`, `state`, `result`, `url`, `createdDate`, `finishedDate` |
| `Group` | `azuredevops.krateo.io/v7-1` | `organization`, `scopeDescriptor`, `displayName`, `description` | `descriptor`, `principalName`, `originId`, `domain` |
| `GroupMembership` | `azuredevops.krateo.io/v7-1` | `organization`, `subjectDescriptor`, `containerDescriptor` | `memberDescriptor`, `containerDescriptor` |
| `RepositoryPermission` | `azuredevops.krateo.io/v7-1` | `organization`, `projectId`, `repositoryId` (optional), `subjectDescriptor` (a Group's `vssgp.…`), `permissions {<Action>: Allow\|Deny\|NotSet}` (21 actions, default `NotSet`) | — |
| `FeedPermission` | `azuredevops.krateo.io/v7-1` | `organization`, `project`, `feedId`, `subjectDescriptor` (a Group's `vssgp.…`), `role` (reader, collaborator, contributor, administrator) | — |

Every kind also has `spec.configurationRef` (`{name, namespace}`) and the standard conditions.
`status` fields are append-only once generated.
