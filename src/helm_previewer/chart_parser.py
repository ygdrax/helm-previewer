"""
Helm Chart Parser - Parse and analyze Helm chart structure
"""

import re
import subprocess
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class HelmResource(BaseModel):
    """Model for a Helm chart resource"""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    kind: str
    api_version: str = Field(alias="apiVersion")
    namespace: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    spec: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChartMetadata(BaseModel):
    """Model for Helm chart metadata"""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    version: str
    api_version: str = Field(alias="apiVersion", default="v2")
    description: str | None = None
    type_: str | None = Field(alias="type", default="application")
    keywords: list[str] = Field(default_factory=list)
    home: str | None = None
    sources: list[str] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    maintainers: list[dict[str, str]] = Field(default_factory=list)


class ChartData(BaseModel):
    """Model for complete chart data"""

    path: str
    name: str
    metadata: ChartMetadata
    templates: list[HelmResource] = Field(default_factory=list)
    values: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    resources: list[HelmResource] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class HelmChartParser:
    """Parser for Helm charts that extracts structure and relationships"""

    def __init__(self):
        self.supported_kinds = {
            "Deployment",
            "Service",
            "ConfigMap",
            "Secret",
            "Ingress",
            "StatefulSet",
            "DaemonSet",
            "Job",
            "CronJob",
            "PersistentVolume",
            "PersistentVolumeClaim",
            "ServiceAccount",
            "Role",
            "RoleBinding",
            "ClusterRole",
            "ClusterRoleBinding",
            "HorizontalPodAutoscaler",
            "NetworkPolicy",
            "Pod",
            "ReplicaSet",
        }

    async def parse_chart(self, chart_path: str) -> ChartData:
        """
        Parse a Helm chart and extract its structure

        Args:
            chart_path: Path to chart directory or chart name

        Returns:
            ChartData containing chart structure and metadata
        """
        chart_path = Path(chart_path)

        if not chart_path.exists():
            raise FileNotFoundError(f"Chart path does not exist: {chart_path}")

        if not chart_path.is_dir():
            raise ValueError(f"Chart path must be a directory: {chart_path}")

        # Parse Chart.yaml
        chart_metadata = await self._parse_chart_metadata(chart_path)

        # Parse values.yaml
        values = await self._parse_values(chart_path)

        # Parse templates
        templates = await self._parse_templates(chart_path, values)

        # Deduplicate resources (in case of any parsing issues)
        templates = self._deduplicate_resources(templates)

        # Extract dependencies
        dependencies = await self._extract_dependencies(chart_path)

        # Analyze relationships
        relationships = self._analyze_relationships(templates)

        # Generate summary
        summary = self._generate_summary(templates, dependencies)

        return ChartData(
            path=str(chart_path.absolute()),
            name=chart_path.name,
            metadata=chart_metadata,
            templates=templates,
            values=values,
            dependencies=dependencies,
            resources=templates,
            relationships=relationships,
            summary=summary,
        )

    async def _parse_chart_metadata(self, chart_path: Path) -> ChartMetadata:
        """Parse Chart.yaml file"""
        chart_file = chart_path / "Chart.yaml"

        if not chart_file.exists():
            # Try Chart.yml as fallback
            chart_file = chart_path / "Chart.yml"

        if not chart_file.exists():
            # Create minimal metadata if no Chart.yaml found
            return ChartMetadata(
                name=chart_path.name,
                version="0.1.0",
                description=f"Chart at {chart_path}",
            )

        with open(chart_file, encoding="utf-8") as f:
            chart_data = yaml.safe_load(f)

        return ChartMetadata(**chart_data)

    async def _parse_values(self, chart_path: Path) -> dict[str, Any]:
        """Parse values.yaml file"""
        values_file = chart_path / "values.yaml"

        if not values_file.exists():
            # Try values.yml as fallback
            values_file = chart_path / "values.yml"

        if not values_file.exists():
            return {}

        try:
            with open(values_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Warning: Failed to parse values.yaml: {e}")
            return {}

    async def _parse_templates(
        self, chart_path: Path, values: dict[str, Any]
    ) -> list[HelmResource]:
        """Parse template files and render them with values"""
        templates_dir = chart_path / "templates"

        if not templates_dir.exists():
            return []

        resources = []

        # Try to render all templates at once with helm template command
        try:
            rendered_resources = await self._render_all_templates(chart_path, values)
            if rendered_resources:
                return rendered_resources
        except Exception as e:
            print(f"Warning: Failed to render templates with helm: {e}")

        # Fallback: Parse individual template files
        for template_file in templates_dir.rglob("*.yaml"):
            if template_file.name.startswith("_"):
                continue  # Skip helpers

            try:
                raw_resources = await self._parse_raw_template(template_file)
                resources.extend(raw_resources)
            except Exception as e:
                print(f"Warning: Failed to parse template {template_file}: {e}")

        return resources

    async def _render_all_templates(
        self, chart_path: Path, values: dict[str, Any]
    ) -> list[HelmResource]:
        """Render all templates using helm template command"""
        try:
            # Use helm template command to render all templates at once
            cmd = [
                "helm",
                "template",
                "test-release",
                str(chart_path),
                "--values",
                str(chart_path / "values.yaml")
                if (chart_path / "values.yaml").exists()
                else "/dev/null",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise Exception(f"Helm template failed: {result.stderr}")

            # Parse the rendered YAML
            resources = []
            for doc in yaml.safe_load_all(result.stdout):
                if doc and isinstance(doc, dict) and "kind" in doc:
                    try:
                        resource = HelmResource(
                            name=doc.get("metadata", {}).get("name", "unknown"),
                            kind=doc.get("kind"),
                            api_version=doc.get("apiVersion", "v1"),
                            namespace=doc.get("metadata", {}).get("namespace"),
                            labels=doc.get("metadata", {}).get("labels", {}),
                            annotations=doc.get("metadata", {}).get("annotations", {}),
                            spec=doc.get("spec", {}),
                            metadata=doc.get("metadata", {}),
                        )
                        resources.append(resource)
                    except Exception as e:
                        print(f"Warning: Failed to parse resource: {e}")

            return resources

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            # Fallback if helm is not available
            raise Exception("Helm command not available") from e

    async def _parse_raw_template(self, template_file: Path) -> list[HelmResource]:
        """Parse template file without rendering (basic YAML parsing)"""
        resources = []

        try:
            with open(template_file, encoding="utf-8") as f:
                content = f.read()

            # Simple template variable replacement for basic parsing
            content = re.sub(r"\{\{.*?\}\}", '""', content)

            for doc in yaml.safe_load_all(content):
                if doc and isinstance(doc, dict) and "kind" in doc:
                    try:
                        resource = HelmResource(
                            name=doc.get("metadata", {}).get("name", "unknown"),
                            kind=doc.get("kind"),
                            api_version=doc.get("apiVersion", "v1"),
                            namespace=doc.get("metadata", {}).get("namespace"),
                            labels=doc.get("metadata", {}).get("labels", {}),
                            annotations=doc.get("metadata", {}).get("annotations", {}),
                            spec=doc.get("spec", {}),
                            metadata=doc.get("metadata", {}),
                        )
                        resources.append(resource)
                    except Exception as e:
                        print(
                            f"Warning: Failed to parse resource from "
                            f"{template_file}: {e}"
                        )

        except Exception as e:
            print(f"Warning: Failed to read template {template_file}: {e}")

        return resources

    def _deduplicate_resources(
        self, resources: list[HelmResource]
    ) -> list[HelmResource]:
        """Remove duplicate resources based on name, kind, and namespace"""
        seen = set()
        deduplicated = []

        for resource in resources:
            # Create a unique key for each resource
            key = (resource.name, resource.kind, resource.namespace or "default")
            if key not in seen:
                seen.add(key)
                deduplicated.append(resource)

        return deduplicated

    async def _extract_dependencies(self, chart_path: Path) -> list[dict[str, Any]]:
        """Extract chart dependencies"""
        dependencies = []

        # Check Chart.yaml for dependencies
        chart_file = chart_path / "Chart.yaml"
        if chart_file.exists():
            with open(chart_file, encoding="utf-8") as f:
                chart_data = yaml.safe_load(f)
                dependencies.extend(chart_data.get("dependencies", []))

        # Check charts/ directory for subcharts
        charts_dir = chart_path / "charts"
        if charts_dir.exists():
            for subchart in charts_dir.iterdir():
                if subchart.is_dir():
                    dependencies.append(
                        {
                            "name": subchart.name,
                            "version": "unknown",
                            "repository": "file://./charts/" + subchart.name,
                        }
                    )

        return dependencies

    def _analyze_relationships(
        self, resources: list[HelmResource]
    ) -> list[dict[str, Any]]:
        """Analyze relationships between resources with enhanced detection
        for key components"""
        relationships = []

        # Create a lookup for resources by name and kind
        resource_map = {(r.name, r.kind): r for r in resources}
        resource_by_kind = {}
        for r in resources:
            if r.kind not in resource_by_kind:
                resource_by_kind[r.kind] = []
            resource_by_kind[r.kind].append(r)

        for resource in resources:
            # Service relationships
            if resource.kind == "Service":
                # Find deployments/statefulsets that this service exposes
                selector = resource.spec.get("selector", {})
                for target_resource in resources:
                    if target_resource.kind in [
                        "Deployment",
                        "StatefulSet",
                        "DaemonSet",
                    ]:
                        target_labels = (
                            target_resource.spec.get("template", {})
                            .get("metadata", {})
                            .get("labels", {})
                        )
                        if self._labels_match(selector, target_labels):
                            relationships.append(
                                {
                                    "source": {
                                        "name": resource.name,
                                        "kind": resource.kind,
                                    },
                                    "target": {
                                        "name": target_resource.name,
                                        "kind": target_resource.kind,
                                    },
                                    "type": "exposes",
                                }
                            )

            # Ingress relationships
            elif resource.kind == "Ingress":
                # Find services that this ingress routes to
                rules = resource.spec.get("rules", [])
                for rule in rules:
                    paths = rule.get("http", {}).get("paths", [])
                    for path in paths:
                        service_name = (
                            path.get("backend", {}).get("service", {}).get("name")
                        )
                        if service_name and (service_name, "Service") in resource_map:
                            relationships.append(
                                {
                                    "source": {
                                        "name": resource.name,
                                        "kind": resource.kind,
                                    },
                                    "target": {"name": service_name, "kind": "Service"},
                                    "type": "routes_to",
                                }
                            )

            # Deployment relationships
            elif resource.kind in ["Deployment", "StatefulSet", "DaemonSet"]:
                # Check for ServiceAccount usage
                service_account_name = (
                    resource.spec.get("template", {})
                    .get("spec", {})
                    .get("serviceAccountName")
                )
                if (
                    service_account_name
                    and (service_account_name, "ServiceAccount") in resource_map
                ):
                    relationships.append(
                        {
                            "source": {
                                "name": service_account_name,
                                "kind": "ServiceAccount",
                            },
                            "target": {"name": resource.name, "kind": resource.kind},
                            "type": "authenticates",
                        }
                    )

                # Check for ConfigMap and Secret usage
                containers = (
                    resource.spec.get("template", {})
                    .get("spec", {})
                    .get("containers", [])
                )
                for container in containers:
                    # Check environment variables
                    env_vars = container.get("env", [])
                    for env_var in env_vars:
                        if "valueFrom" in env_var:
                            value_from = env_var["valueFrom"]
                            if "configMapKeyRef" in value_from:
                                cm_name = value_from["configMapKeyRef"].get("name")
                                if cm_name and (cm_name, "ConfigMap") in resource_map:
                                    relationships.append(
                                        {
                                            "source": {
                                                "name": cm_name,
                                                "kind": "ConfigMap",
                                            },
                                            "target": {
                                                "name": resource.name,
                                                "kind": resource.kind,
                                            },
                                            "type": "configures",
                                        }
                                    )
                            elif "secretKeyRef" in value_from:
                                secret_name = value_from["secretKeyRef"].get("name")
                                if (
                                    secret_name
                                    and (secret_name, "Secret") in resource_map
                                ):
                                    relationships.append(
                                        {
                                            "source": {
                                                "name": secret_name,
                                                "kind": "Secret",
                                            },
                                            "target": {
                                                "name": resource.name,
                                                "kind": resource.kind,
                                            },
                                            "type": "provides_secret",
                                        }
                                    )

                    # Check volume mounts
                    volume_mounts = container.get("volumeMounts", [])
                    for volume_mount in volume_mounts:
                        volume_name = volume_mount.get("name")
                        # Find corresponding volume in spec
                        volumes = (
                            resource.spec.get("template", {})
                            .get("spec", {})
                            .get("volumes", [])
                        )
                        for volume in volumes:
                            if volume.get("name") == volume_name:
                                if "configMap" in volume:
                                    cm_name = volume["configMap"].get("name")
                                    if (
                                        cm_name
                                        and (cm_name, "ConfigMap") in resource_map
                                    ):
                                        relationships.append(
                                            {
                                                "source": {
                                                    "name": cm_name,
                                                    "kind": "ConfigMap",
                                                },
                                                "target": {
                                                    "name": resource.name,
                                                    "kind": resource.kind,
                                                },
                                                "type": "mounts",
                                            }
                                        )
                                elif "secret" in volume:
                                    secret_name = volume["secret"].get("secretName")
                                    if (
                                        secret_name
                                        and (secret_name, "Secret") in resource_map
                                    ):
                                        relationships.append(
                                            {
                                                "source": {
                                                    "name": secret_name,
                                                    "kind": "Secret",
                                                },
                                                "target": {
                                                    "name": resource.name,
                                                    "kind": resource.kind,
                                                },
                                                "type": "mounts",
                                            }
                                        )
                                elif "persistentVolumeClaim" in volume:
                                    pvc_name = volume["persistentVolumeClaim"].get(
                                        "claimName"
                                    )
                                    if (
                                        pvc_name
                                        and (pvc_name, "PersistentVolumeClaim")
                                        in resource_map
                                    ):
                                        relationships.append(
                                            {
                                                "source": {
                                                    "name": pvc_name,
                                                    "kind": "PersistentVolumeClaim",
                                                },
                                                "target": {
                                                    "name": resource.name,
                                                    "kind": resource.kind,
                                                },
                                                "type": "provides_storage",
                                            }
                                        )

            # Role and RoleBinding relationships
            elif resource.kind == "RoleBinding":
                # Link RoleBinding to ServiceAccount
                subjects = resource.spec.get("subjects", [])
                for subject in subjects:
                    if subject.get("kind") == "ServiceAccount":
                        sa_name = subject.get("name")
                        if sa_name and (sa_name, "ServiceAccount") in resource_map:
                            relationships.append(
                                {
                                    "source": {
                                        "name": resource.name,
                                        "kind": resource.kind,
                                    },
                                    "target": {
                                        "name": sa_name,
                                        "kind": "ServiceAccount",
                                    },
                                    "type": "grants_permissions",
                                }
                            )

                # Link RoleBinding to Role
                role_ref = resource.spec.get("roleRef", {})
                if role_ref.get("kind") == "Role":
                    role_name = role_ref.get("name")
                    if role_name and (role_name, "Role") in resource_map:
                        relationships.append(
                            {
                                "source": {"name": role_name, "kind": "Role"},
                                "target": {
                                    "name": resource.name,
                                    "kind": resource.kind,
                                },
                                "type": "defines_permissions",
                            }
                        )

        return relationships

    def _labels_match(self, selector: dict[str, str], labels: dict[str, str]) -> bool:
        """Check if labels match a selector"""
        for key, value in selector.items():
            if labels.get(key) != value:
                return False
        return True

    def _generate_summary(
        self, resources: list[HelmResource], dependencies: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate enhanced summary statistics with focus on key components"""
        kind_counts = {}
        for resource in resources:
            kind_counts[resource.kind] = kind_counts.get(resource.kind, 0) + 1

        # Key component analysis
        key_components = {
            "service_accounts": kind_counts.get("ServiceAccount", 0),
            "deployments": kind_counts.get("Deployment", 0)
            + kind_counts.get("StatefulSet", 0)
            + kind_counts.get("DaemonSet", 0),
            "services": kind_counts.get("Service", 0),
            "ingresses": kind_counts.get("Ingress", 0),
        }

        # Architecture completeness score
        architecture_score = 0
        if key_components["deployments"] > 0:
            architecture_score += 25  # Has workloads
        if key_components["services"] > 0:
            architecture_score += 25  # Has service layer
        if key_components["ingresses"] > 0:
            architecture_score += 25  # Has ingress
        if key_components["service_accounts"] > 0:
            architecture_score += 25  # Has security

        # Security analysis
        has_rbac = any(
            kind in kind_counts
            for kind in ["Role", "RoleBinding", "ClusterRole", "ClusterRoleBinding"]
        )
        has_secrets = kind_counts.get("Secret", 0) > 0
        has_config = kind_counts.get("ConfigMap", 0) > 0

        return {
            "total_resources": len(resources),
            "resource_types": len(kind_counts),
            "kind_counts": kind_counts,
            "dependencies_count": len(dependencies),
            # Key component flags
            "has_ingress": any(r.kind == "Ingress" for r in resources),
            "has_services": any(r.kind == "Service" for r in resources),
            "has_deployments": any(
                r.kind in ["Deployment", "StatefulSet", "DaemonSet"] for r in resources
            ),
            "has_service_accounts": any(r.kind == "ServiceAccount" for r in resources),
            # Enhanced analysis
            "key_components": key_components,
            "architecture_score": architecture_score,
            "architecture_grade": self._get_architecture_grade(architecture_score),
            "has_rbac": has_rbac,
            "has_secrets": has_secrets,
            "has_config": has_config,
            "security_score": self._calculate_security_score(
                has_rbac, has_secrets, key_components["service_accounts"] > 0
            ),
            # Resource categories
            "workload_resources": sum(
                kind_counts.get(k, 0)
                for k in ["Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"]
            ),
            "networking_resources": sum(
                kind_counts.get(k, 0) for k in ["Service", "Ingress", "NetworkPolicy"]
            ),
            "storage_resources": sum(
                kind_counts.get(k, 0)
                for k in ["PersistentVolume", "PersistentVolumeClaim"]
            ),
            "config_resources": sum(
                kind_counts.get(k, 0) for k in ["ConfigMap", "Secret"]
            ),
            "security_resources": sum(
                kind_counts.get(k, 0)
                for k in [
                    "ServiceAccount",
                    "Role",
                    "RoleBinding",
                    "ClusterRole",
                    "ClusterRoleBinding",
                ]
            ),
        }

    def _get_architecture_grade(self, score: int) -> str:
        """Get architecture grade based on completeness score"""
        if score >= 100:
            return "A+ (Complete)"
        elif score >= 75:
            return "A (Excellent)"
        elif score >= 50:
            return "B (Good)"
        elif score >= 25:
            return "C (Basic)"
        else:
            return "D (Incomplete)"

    def _calculate_security_score(
        self, has_rbac: bool, has_secrets: bool, has_service_accounts: bool
    ) -> int:
        """Calculate security score based on security features"""
        score = 0
        if has_service_accounts:
            score += 40
        if has_rbac:
            score += 40
        if has_secrets:
            score += 20
        return score
