{{- define "scalable-app-chart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "scalable-app-chart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "scalable-app-chart.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "scalable-app-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "scalable-app-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "scalable-app-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "scalable-app-chart.postgresSecretName" -}}
{{- if .Values.postgresql.existingSecret -}}
{{- .Values.postgresql.existingSecret -}}
{{- else -}}
{{- printf "%s-db" (include "scalable-app-chart.fullname" .) -}}
{{- end -}}
{{- end -}}
