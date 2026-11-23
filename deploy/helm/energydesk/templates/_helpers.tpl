{{/* Nom de base des ressources (ex. "energydesk" -> energydesk-api, energydesk-worker...). */}}
{{- define "ed.fullname" -}}
{{- .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}

{{/* Labels communs a toutes les ressources. */}}
{{- define "ed.labels" -}}
app.kubernetes.io/name: energydesk
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Values.image.tag | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: energydesk
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
energydesk/environment: {{ .Values.environment }}
{{- end -}}

{{/* Labels de selection d'un composant. Usage : include "ed.selector" (dict "ctx" . "component" "api") */}}
{{- define "ed.selector" -}}
app.kubernetes.io/name: energydesk
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Image applicative versionnee. Usage : include "ed.image" (dict "ctx" . "component" "api") */}}
{{- define "ed.image" -}}
{{- printf "%s/%s/energydesk-%s:%s" .ctx.Values.image.registry (lower .ctx.Values.image.owner) .component .ctx.Values.image.tag -}}
{{- end -}}

{{- define "ed.dbHost" -}}
{{- if .Values.postgres.enabled -}}
{{- printf "%s-postgres" (include "ed.fullname" .) -}}
{{- else -}}
{{- required "externalDatabase.host est obligatoire quand postgres.enabled=false" .Values.externalDatabase.host -}}
{{- end -}}
{{- end -}}

{{- define "ed.s3Endpoint" -}}
{{- if .Values.s3.endpointUrl -}}
{{- .Values.s3.endpointUrl -}}
{{- else if .Values.minio.enabled -}}
{{- printf "http://%s-minio:9000" (include "ed.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/* Variable d'environnement lue dans le Secret. Usage : include "ed.secretEnv" (dict "ctx" . "name" "DB_PASSWORD") */}}
{{- define "ed.secretEnv" -}}
- name: {{ .name }}
  valueFrom:
    secretKeyRef:
      name: {{ .ctx.Values.existingSecret }}
      key: {{ .name }}
{{- end -}}

{{/* Annotation qui force un redemarrage des pods quand la ConfigMap change. */}}
{{- define "ed.configChecksum" -}}
checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
{{- end -}}
