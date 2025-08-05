"""
Helm Chart Parser - Parse and analyze Helm chart structure
"""

import os
import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import tempfile
import subprocess


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
    
    def parse_chart(self, chart_path: str) -> Dict[str, Any]:
        """
        Parse a Helm chart and extract its structure
        
        Args:
            chart_path: Path to chart directory or chart name
            
        Returns:
            Dictionary containing chart structure and metadata
        """
        chart_path = Path(chart_path)
        
        if not chart_path.exists():
            raise FileNotFoundError(f"Chart path does not exist: {chart_path}")
        
        if not chart_path.is_dir():
            raise ValueError(f"Chart path must be a directory: {chart_path}")
        
        chart_data = {
            'path': str(chart_path.absolute()),
            'name': chart_path.name,
            'templates': [],
            'values': {},
            'dependencies': [],
            'metadata': {},
            'relationships': []
        }
        
        # Parse Chart.yaml
        chart_yaml_path = chart_path / 'Chart.yaml'
        if chart_yaml_path.exists():
            chart_data['metadata'] = self._parse_chart_yaml(chart_yaml_path)
            chart_data['name'] = chart_data['metadata'].get('name', chart_path.name)
            chart_data['version'] = chart_data['metadata'].get('version', '0.0.0')
            chart_data['description'] = chart_data['metadata'].get('description', '')
            chart_data['dependencies'] = chart_data['metadata'].get('dependencies', [])
        
        # Parse values.yaml
        values_yaml_path = chart_path / 'values.yaml'
        if values_yaml_path.exists():
            chart_data['values'] = self._parse_values_yaml(values_yaml_path)
        
        # Parse templates
        templates_dir = chart_path / 'templates'
        if templates_dir.exists() and templates_dir.is_dir():
            chart_data['templates'] = self._parse_templates(templates_dir, chart_data['values'])
        
        # Analyze relationships
        chart_data['relationships'] = self._analyze_relationships(chart_data['templates'])
        
        return chart_data
    
    def _parse_chart_yaml(self, chart_yaml_path: Path) -> Dict[str, Any]:
        """Parse Chart.yaml file"""
        try:
            with open(chart_yaml_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not parse Chart.yaml: {e}")
            return {}
    
    def _parse_values_yaml(self, values_yaml_path: Path) -> Dict[str, Any]:
        """Parse values.yaml file"""
        try:
            with open(values_yaml_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not parse values.yaml: {e}")
            return {}
    
    def _parse_templates(self, templates_dir: Path, values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse all template files in the templates directory"""
        templates = []
        
        for template_file in templates_dir.rglob('*.yaml'):
            if template_file.name.startswith('_'):
                continue  # Skip helper templates
            
            try:
                template_data = self._parse_template_file(template_file, values)
                if template_data:
                    templates.extend(template_data)
            except Exception as e:
                print(f"Warning: Could not parse template {template_file}: {e}")
        
        return templates
    
    def _parse_template_file(self, template_file: Path, values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse a single template file"""
        templates = []
        
        try:
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Try to render template with basic values to extract structure
            rendered_content = self._basic_template_render(content, values)
            
            # Split by YAML document separator
            documents = rendered_content.split('---')
            
            for i, doc in enumerate(documents):
                doc = doc.strip()
                if not doc:
                    continue
                
                try:
                    parsed = yaml.safe_load(doc)
                    if parsed and isinstance(parsed, dict):
                        template_info = {
                            'file': str(template_file.relative_to(template_file.parent.parent)),
                            'name': parsed.get('metadata', {}).get('name', f"unnamed-{i}"),
                            'kind': parsed.get('kind', 'Unknown'),
                            'apiVersion': parsed.get('apiVersion', ''),
                            'metadata': parsed.get('metadata', {}),
                            'spec': parsed.get('spec', {}),
                            'data': parsed.get('data', {}),
                            'raw_content': doc,
                            'template_variables': self._extract_template_variables(content)
                        }
                        templates.append(template_info)
                except yaml.YAMLError:
                    # If YAML parsing fails, still record the template
                    template_info = {
                        'file': str(template_file.relative_to(template_file.parent.parent)),
                        'name': template_file.stem,
                        'kind': 'Template',
                        'apiVersion': '',
                        'metadata': {},
                        'spec': {},
                        'data': {},
                        'raw_content': doc,
                        'template_variables': self._extract_template_variables(content),
                        'parse_error': True
                    }
                    templates.append(template_info)
        
        except Exception as e:
            print(f"Error parsing template file {template_file}: {e}")
        
        return templates
    
    def _basic_template_render(self, content: str, values: Dict[str, Any]) -> str:
        """Basic template rendering to extract structure"""
        # Replace common Helm template functions with placeholder values
        replacements = {
            r'\{\{\s*\.Chart\.Name\s*\}\}': 'chart-name',
            r'\{\{\s*\.Chart\.Version\s*\}\}': '1.0.0',
            r'\{\{\s*\.Release\.Name\s*\}\}': 'release-name',
            r'\{\{\s*\.Release\.Namespace\s*\}\}': 'default',
            r'\{\{\s*\.Values\.([^}]+)\}\}': lambda m: self._get_nested_value(values, m.group(1), 'placeholder'),
            r'\{\{\s*include\s+"[^"]*"\s+\.\s*\}\}': 'included-template',
            r'\{\{\s*template\s+"[^"]*"\s+\.\s*\}\}': 'template-output',
            r'\{\{\s*[^}]+\}\}': 'template-value'
        }
        
        rendered = content
        for pattern, replacement in replacements.items():
            if callable(replacement):
                rendered = re.sub(pattern, replacement, rendered)
            else:
                rendered = re.sub(pattern, replacement, rendered)
        
        return rendered
    
    def _get_nested_value(self, values: Dict[str, Any], path: str, default: str) -> str:
        """Get nested value from values dict using dot notation"""
        try:
            keys = path.split('.')
            current = values
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return str(current) if current is not None else default
        except:
            return default
    
    def _extract_template_variables(self, content: str) -> List[str]:
        """Extract template variables from content"""
        # Find all {{...}} expressions
        pattern = r'\{\{\s*([^}]+)\s*\}\}'
        matches = re.findall(pattern, content)
        
        variables = []
        for match in matches:
            # Clean up the variable expression
            var = match.strip()
            if var and not var.startswith('-') and not var.endswith('-'):
                variables.append(var)
        
        return list(set(variables))  # Remove duplicates
    
    def _analyze_relationships(self, templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze relationships between templates"""
        relationships = []
        
        for template in templates:
            # Find references in spec and metadata
            refs = self._find_references(template)
            for ref in refs:
                relationships.append({
                    'source': template['name'],
                    'source_kind': template['kind'],
                    'target': ref['target'],
                    'target_kind': ref['target_kind'],
                    'relationship_type': ref['type'],
                    'field': ref['field']
                })
        
        return relationships
    
    def _find_references(self, template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find references to other resources in a template"""
        references = []
        
        def search_dict(obj: Any, path: str = ""):
            """Recursively search for references in dictionaries"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Look for common reference patterns
                    if key in ['name', 'serviceName', 'secretName', 'configMapName']:
                        if isinstance(value, str) and not value.startswith('{{'):
                            references.append({
                                'target': value,
                                'target_kind': self._guess_kind_from_field(key),
                                'type': 'reference',
                                'field': current_path
                            })
                    
                    search_dict(value, current_path)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    search_dict(item, f"{path}[{i}]")
        
        # Search in spec and other relevant sections
        search_dict(template.get('spec', {}), 'spec')
        search_dict(template.get('metadata', {}), 'metadata')
        search_dict(template.get('data', {}), 'data')
        
        return references
    
    def _guess_kind_from_field(self, field_name: str) -> str:
        """Guess Kubernetes resource kind from field name"""
        kind_mapping = {
            'serviceName': 'Service',
            'secretName': 'Secret',
            'configMapName': 'ConfigMap',
            'name': 'Unknown'
        }
        return kind_mapping.get(field_name, 'Unknown')
