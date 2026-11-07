{{/*
  azuredevops-provider-kog.kindEnabled: whether this release renders a kind.

  Called as (list . "<Kind>") at the top of every rd-* and configmap-* template. The result is
  "true" or empty, so it can be used directly in an `if`.

  EMPTY MEANS ALL, deliberately. The CDC stores defaults on the composition, so a default list of
  names would freeze forever and never render a kind added by a later chart version.
*/}}
{{- define "azuredevops-provider-kog.kindEnabled" -}}
{{- $root := index . 0 -}}
{{- $kind := index . 1 -}}
{{- if or (not $root.Values.kinds) (has $kind $root.Values.kinds) -}}true{{- end -}}
{{- end -}}
