"""
Helm Chart Parser - Parse and analyze Helm chart structure
"""

import os
import yaml
import json
import re
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class HelmResource(BaseModel):
    """Model for a Helm chart resource"""
    name: str
    kind: str
    api_version: str = Field(alias="apiVersion")
    namespace: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    spec: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True


class ChartMetadata(BaseModel):
    """Model for Helm chart metadata"""
    name: str
    version: str
    api_version: str = Field(alias="apiVersion", default="v2")
    description: Optional[str] = None
    type_: Optional[str] = Field(alias="type", default="application")
    keywords: List[str] = Field(default_factory=list)
    home: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    maintainers: List[Dict[str, str]] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True


class ChartData(BaseModel):
    """Model for complete chart data"""
    path: str
    name: str
    metadata: ChartMetadata
    templates: List[HelmResource] = Field(default_factory=list)
    values: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    resources: List[HelmResource] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class HelmChartParser:
    """Parser for Helm charts that extracts structure and relationships"""
    
    def __init__(self):
        self.supported_kinds = {
            'Deployment', 'Service', 'ConfigMap', 'Secret', 'Ingress',
            'StatefulSet', 'DaemonSet', 'Job', 'CronJob', 'PersistentVolume',
            'PersistentVolumeClaim', 'ServiceAccount', 'Role', 'RoleBinding',
            'ClusterRole', 'ClusterRoleBinding', 'HorizontalPodAutoscaler',
            'NetworkPolicy', 'Pod', 'ReplicaSet'
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
            summary=summary
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
                description=f"Chart at {chart_path}"
            )
        
        with open(chart_file, 'r', encoding='utf-8') as f:
            chart_data = yaml.safe_load(f)
        
        return ChartMetadata(**chart_data)
    
    async def _parse_values(self, chart_path: Path) -> Dict[str, Any]:
        """Parse values.yaml file"""
        values_file = chart_path / "values.yaml"
        
        if not values_file.exists():
            # Try values.yml as fallback
            values_file = chart_path / "values.yml"
            
        if not values_file.exists():
            return {}
        
        try:
            with open(values_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Warning: Failed to parse values.yaml: {e}")
            return {}
    
    async def _parse_templates(self, chart_path: Path, values: Dict[str, Any]) -> List[HelmResource]:
        """Parse template files and render them with values"""
        templates_dir = chart_path / "templates"
        
        if not templates_dir.exists():
            return []
        
        resources = []
        
        # Find all template files
        for template_file in templates_dir.rglob("*.yaml"):
            if template_file.name.startswith('_'):
                continue  # Skip helpers
                
            try:
                # Try to render the template with helm template command
                rendered_resources = await self._render_template(chart_path, template_file, values)
                resources.extend(rendered_resources)
            except Exception as e:
                print(f"Warning: Failed to parse template {template_file}: {e}")
                # Fallback to raw parsing
                raw_resources = await self._parse_raw_template(template_file)
                resources.extend(raw_resources)
        
        return resources
    
    async def _render_template(self, chart_path: Path, template_file: Path, values: Dict[str, Any]) -> List[HelmResource]:
        """Render template using helm template command"""
        try:
            # Use helm template command to render
            cmd = [
                "helm", "template", "test-release", str(chart_path),
                "--values", str(chart_path / "values.yaml") if (chart_path / "values.yaml").exists() else "/dev/null"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Helm template failed: {result.stderr}")
            
            # Parse the rendered YAML
            resources = []
            for doc in yaml.safe_load_all(result.stdout):
                if doc and isinstance(doc, dict) and 'kind' in doc:
                    try:
                        resource = HelmResource(
                            name=doc.get('metadata', {}).get('name', 'unknown'),
                            kind=doc.get('kind'),
                            api_version=doc.get('apiVersion', 'v1'),
                            namespace=doc.get('metadata', {}).get('namespace'),
                            labels=doc.get('metadata', {}).get('labels', {}),
                            annotations=doc.get('metadata', {}).get('annotations', {}),
                            spec=doc.get('spec', {}),
                            metadata=doc.get('metadata', {})
                        )
                        resources.append(resource)
                    except Exception as e:
                        print(f"Warning: Failed to parse resource: {e}")
            
            return resources
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback if helm is not available
            return await self._parse_raw_template(template_file)
    
    async def _parse_raw_template(self, template_file: Path) -> List[HelmResource]:
        """Parse template file without rendering (basic YAML parsing)"""
        resources = []
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple template variable replacement for basic parsing
            content = re.sub(r'\{\{.*?\}\}', '""', content)
            
            for doc in yaml.safe_load_all(content):
                if doc and isinstance(doc, dict) and 'kind' in doc:
                    try:
                        resource = HelmResource(
                            name=doc.get('metadata', {}).get('name', 'unknown'),
                            kind=doc.get('kind'),
                            api_version=doc.get('apiVersion', 'v1'),
                            namespace=doc.get('metadata', {}).get('namespace'),
                            labels=doc.get('metadata', {}).get('labels', {}),
                            annotations=doc.get('metadata', {}).get('annotations', {}),
                            spec=doc.get('spec', {}),
                            metadata=doc.get('metadata', {})
                        )
                        resources.append(resource)
                    except Exception as e:
                        print(f"Warning: Failed to parse resource from {template_file}: {e}")
        
        except Exception as e:
            print(f"Warning: Failed to read template {template_file}: {e}")
        
        return resources
    
    async def _extract_dependencies(self, chart_path: Path) -> List[Dict[str, Any]]:
        """Extract chart dependencies"""
        dependencies = []
        
        # Check Chart.yaml for dependencies
        chart_file = chart_path / "Chart.yaml"
        if chart_file.exists():
            with open(chart_file, 'r', encoding='utf-8') as f:
                chart_data = yaml.safe_load(f)
                dependencies.extend(chart_data.get('dependencies', []))
        
        # Check charts/ directory for subcharts
        charts_dir = chart_path / "charts"
        if charts_dir.exists():
            for subchart in charts_dir.iterdir():
                if subchart.is_dir():
                    dependencies.append({
                        'name': subchart.name,
                        'version': 'unknown',
                        'repository': 'file://./charts/' + subchart.name
                    })
        
        return dependencies
    
    def _analyze_relationships(self, resources: List[HelmResource]) -> List[Dict[str, Any]]:
        """Analyze relationships between resources"""
        relationships = []
        
        # Create a lookup for resources by name and kind
        resource_map = {(r.name, r.kind): r for r in resources}
        
        for resource in resources:
            if resource.kind == 'Service':
                # Find deployments that this service might target
                selector = resource.spec.get('selector', {})
                for target_resource in resources:
                    if target_resource.kind in ['Deployment', 'StatefulSet']:
                        target_labels = target_resource.spec.get('template', {}).get('metadata', {}).get('labels', {})
                        if self._labels_match(selector, target_labels):
                            relationships.append({
                                'source': {'name': resource.name, 'kind': resource.kind},
                                'target': {'name': target_resource.name, 'kind': target_resource.kind},
                                'type': 'exposes'
                            })
            
            elif resource.kind == 'Ingress':
                # Find services that this ingress routes to
                rules = resource.spec.get('rules', [])
                for rule in rules:
                    paths = rule.get('http', {}).get('paths', [])
                    for path in paths:
                        service_name = path.get('backend', {}).get('service', {}).get('name')
                        if service_name and (service_name, 'Service') in resource_map:
                            relationships.append({
                                'source': {'name': resource.name, 'kind': resource.kind},
                                'target': {'name': service_name, 'kind': 'Service'},
                                'type': 'routes_to'
                            })
        
        return relationships
    
    def _labels_match(self, selector: Dict[str, str], labels: Dict[str, str]) -> bool:
        """Check if labels match a selector"""
        for key, value in selector.items():
            if labels.get(key) != value:
                return False
        return True
    
    def _generate_summary(self, resources: List[HelmResource], dependencies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics"""
        kind_counts = {}
        for resource in resources:
            kind_counts[resource.kind] = kind_counts.get(resource.kind, 0) + 1
        
        return {
            'total_resources': len(resources),
            'resource_types': len(kind_counts),
            'kind_counts': kind_counts,
            'dependencies_count': len(dependencies),
            'has_ingress': any(r.kind == 'Ingress' for r in resources),
            'has_services': any(r.kind == 'Service' for r in resources),
            'has_deployments': any(r.kind == 'Deployment' for r in resources),
        }
