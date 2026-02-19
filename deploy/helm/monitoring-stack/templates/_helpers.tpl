{{/*
Common template helpers for the monitoring-stack chart.
These functions generate consistent naming, labels, and selectors
across all resources in the chart.
*/}}

{{/*
Expand the name of the chart, truncated to 63 chars (K8s label limit).
*/}}
{{- define "monitoring-stack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name. Uses release name + chart name, or fullnameOverride.
Truncated to 63 chars for K8s name compliance.
*/}}
{{- define "monitoring-stack.fullname" -}}
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

{{/*
Create chart label value (name-version).
*/}}
{{- define "monitoring-stack.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every resource.
*/}}
{{- define "monitoring-stack.labels" -}}
helm.sh/chart: {{ include "monitoring-stack.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/part-of: {{ include "monitoring-stack.name" . }}
{{- end }}

{{/*
Component-specific labels. Call with a dict containing "context" (root) and "component" (string).
Example: {{ include "monitoring-stack.componentLabels" (dict "context" . "component" "prometheus") }}
*/}}
{{- define "monitoring-stack.componentLabels" -}}
{{ include "monitoring-stack.labels" .context }}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Selector labels for a component. Used in Service selectors and pod template matchLabels.
These must NOT change after initial deployment (StatefulSet constraint).
*/}}
{{- define "monitoring-stack.selectorLabels" -}}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
{{- end }}

{{/*
Component fullname helper. Produces "<release>-<component>" truncated to 63 chars.
*/}}
{{- define "monitoring-stack.componentFullname" -}}
{{- printf "%s-%s" (include "monitoring-stack.fullname" .context) .component | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Namespace to deploy into. Defaults to .Release.Namespace.
*/}}
{{- define "monitoring-stack.namespace" -}}
{{- default .Release.Namespace .Values.namespaceOverride }}
{{- end }}
