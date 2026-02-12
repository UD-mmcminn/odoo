{{- define "odoo.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "odoo.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "odoo.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "odoo.labels" -}}
helm.sh/chart: {{ include "odoo.chart" . }}
app.kubernetes.io/name: {{ include "odoo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "odoo.selectorLabels" -}}
app.kubernetes.io/name: {{ include "odoo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "odoo.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "odoo.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "odoo.secretName" -}}
{{- if .Values.odoo.existingSecret -}}
{{- .Values.odoo.existingSecret -}}
{{- else -}}
{{- printf "%s-secrets" (include "odoo.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "odoo.certificateSecretName" -}}
{{- if .Values.certificate.secretName -}}
{{- .Values.certificate.secretName -}}
{{- else -}}
{{- printf "%s-tls" (include "odoo.fullname" .) -}}
{{- end -}}
{{- end -}}
