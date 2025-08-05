"""
Simple Chart Previewer - A lightweight version without heavy dependencies
"""

import os
import yaml
import json
from pathlib import Path
import re
from typing import Dict, List, Any


class SimpleChartParser:
    """Lightweight chart parser without external dependencies"""
    
    def parse_chart(self, chart_path: str) -> Dict[str, Any]:
        """Parse chart and return structure"""
        chart_path = Path(chart_path)
        
        if not chart_path.exists():
            raise FileNotFoundError(f"Chart path does not exist: {chart_path}")
        
        chart_data = {
            'name': chart_path.name,
            'path': str(chart_path.absolute()),
            'templates': [],
            'values': {},
            'metadata': {},
            'relationships': []
        }
        
        # Parse Chart.yaml
        chart_yaml = chart_path / 'Chart.yaml'
        if chart_yaml.exists():
            try:
                with open(chart_yaml, 'r') as f:
                    chart_data['metadata'] = yaml.safe_load(f) or {}
                    chart_data['name'] = chart_data['metadata'].get('name', chart_path.name)
                    chart_data['version'] = chart_data['metadata'].get('version', '0.0.0')
                    chart_data['description'] = chart_data['metadata'].get('description', '')
            except Exception as e:
                print(f"Warning: Could not parse Chart.yaml: {e}")
        
        # Parse values.yaml
        values_yaml = chart_path / 'values.yaml'
        if values_yaml.exists():
            try:
                with open(values_yaml, 'r') as f:
                    chart_data['values'] = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not parse values.yaml: {e}")
        
        # Parse templates
        templates_dir = chart_path / 'templates'
        if templates_dir.exists():
            chart_data['templates'] = self._parse_templates(templates_dir)
        
        return chart_data
    
    def _parse_templates(self, templates_dir: Path) -> List[Dict[str, Any]]:
        """Parse template files"""
        templates = []
        
        for template_file in templates_dir.glob('*.yaml'):
            if template_file.name.startswith('_'):
                continue
            
            try:
                with open(template_file, 'r') as f:
                    content = f.read()
                
                # Basic template parsing
                docs = content.split('---')
                for doc in docs:
                    doc = doc.strip()
                    if not doc:
                        continue
                    
                    try:
                        # Simple YAML-like parsing for kind and metadata
                        kind = self._extract_field(doc, 'kind')
                        name = self._extract_name(doc)
                        
                        if kind:
                            templates.append({
                                'file': str(template_file.name),
                                'name': name or template_file.stem,
                                'kind': kind,
                                'content_preview': doc[:200] + '...' if len(doc) > 200 else doc
                            })
                    except:
                        # If parsing fails, still record the template
                        templates.append({
                            'file': str(template_file.name),
                            'name': template_file.stem,
                            'kind': 'Template',
                            'content_preview': doc[:200] + '...' if len(doc) > 200 else doc
                        })
            except Exception as e:
                print(f"Warning: Could not parse template {template_file}: {e}")
        
        return templates
    
    def _extract_field(self, content: str, field: str) -> str:
        """Extract field value from YAML-like content"""
        pattern = rf'^{field}:\s*(.+)$'
        match = re.search(pattern, content, re.MULTILINE)
        return match.group(1).strip() if match else ''
    
    def _extract_name(self, content: str) -> str:
        """Extract name from metadata"""
        # Look for metadata.name
        pattern = r'name:\s*(.+)$'
        lines = content.split('\n')
        in_metadata = False
        
        for line in lines:
            if line.strip() == 'metadata:':
                in_metadata = True
                continue
            
            if in_metadata and line.startswith('  name:'):
                name = line.split(':', 1)[1].strip()
                # Remove template expressions for display
                name = re.sub(r'\{\{[^}]+\}\}', 'TEMPLATE', name)
                return name
            
            if in_metadata and line and not line.startswith(' '):
                in_metadata = False
        
        return ''


def simple_visualize_text(chart_data: Dict[str, Any]) -> str:
    """Generate simple text visualization"""
    
    output = []
    output.append("=" * 60)
    output.append(f"HELM CHART ANALYSIS: {chart_data['name']}")
    output.append("=" * 60)
    
    # Chart info
    output.append(f"\n📊 CHART INFORMATION")
    output.append(f"   Name: {chart_data['name']}")
    output.append(f"   Version: {chart_data.get('version', 'Unknown')}")
    output.append(f"   Description: {chart_data.get('description', 'No description')}")
    output.append(f"   Path: {chart_data['path']}")
    
    # Templates
    templates = chart_data.get('templates', [])
    output.append(f"\n🔧 TEMPLATES ({len(templates)})")
    
    if templates:
        # Group by kind
        by_kind = {}
        for template in templates:
            kind = template['kind']
            if kind not in by_kind:
                by_kind[kind] = []
            by_kind[kind].append(template)
        
        for kind, items in by_kind.items():
            output.append(f"\n   {kind} ({len(items)}):")
            for item in items:
                output.append(f"     • {item['name']} ({item['file']})")
    else:
        output.append("   No templates found")
    
    # Values
    values = chart_data.get('values', {})
    if values:
        output.append(f"\n⚙️  CONFIGURABLE VALUES ({len(values)} top-level)")
        for key in list(values.keys())[:10]:  # Show first 10
            value_type = type(values[key]).__name__
            output.append(f"     • {key} ({value_type})")
        if len(values) > 10:
            output.append(f"     ... and {len(values) - 10} more")
    
    # Dependencies
    deps = chart_data.get('metadata', {}).get('dependencies', [])
    if deps:
        output.append(f"\n📦 DEPENDENCIES ({len(deps)})")
        for dep in deps:
            output.append(f"     • {dep.get('name', 'Unknown')} v{dep.get('version', 'Unknown')}")
    
    output.append("\n" + "=" * 60)
    
    return "\n".join(output)


def generate_simple_html(chart_data: Dict[str, Any]) -> str:
    """Generate simple HTML visualization"""
    
    templates = chart_data.get('templates', [])
    
    # Group templates by kind
    by_kind = {}
    for template in templates:
        kind = template['kind']
        if kind not in by_kind:
            by_kind[kind] = []
        by_kind[kind].append(template)
    
    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Helm Chart: {chart_data['name']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }}
        .header h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .info-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .info-card h3 {{
            margin-top: 0;
            color: #333;
        }}
        .templates-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        .template-card {{
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            transition: transform 0.2s;
        }}
        .template-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .kind-badge {{
            display: inline-block;
            padding: 4px 8px;
            background: #007bff;
            color: white;
            border-radius: 4px;
            font-size: 0.8em;
            margin-bottom: 8px;
        }}
        .template-name {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .template-file {{
            font-size: 0.9em;
            color: #666;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            text-align: center;
            margin: 20px 0;
        }}
        .stat {{
            background: #e9ecef;
            padding: 15px;
            border-radius: 8px;
            min-width: 120px;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {chart_data['name']}</h1>
            <p>{chart_data.get('description', 'Helm Chart Analysis')}</p>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-number">{len(templates)}</div>
                <div class="stat-label">Templates</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len(by_kind)}</div>
                <div class="stat-label">Resource Types</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len(chart_data.get('values', {}))}</div>
                <div class="stat-label">Config Values</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len(chart_data.get('metadata', {}).get('dependencies', []))}</div>
                <div class="stat-label">Dependencies</div>
            </div>
        </div>
        
        <div class="info-grid">
            <div class="info-card">
                <h3>📋 Chart Information</h3>
                <p><strong>Name:</strong> {chart_data['name']}</p>
                <p><strong>Version:</strong> {chart_data.get('version', 'Unknown')}</p>
                <p><strong>Path:</strong> {chart_data['path']}</p>
            </div>
            
            <div class="info-card">
                <h3>📦 Dependencies</h3>"""
    
    deps = chart_data.get('metadata', {}).get('dependencies', [])
    if deps:
        for dep in deps:
            html += f"<p>• {dep.get('name', 'Unknown')} v{dep.get('version', 'Unknown')}</p>"
    else:
        html += "<p>No dependencies</p>"
    
    html += """
            </div>
        </div>
        
        <h2>🔧 Templates</h2>
        <div class="templates-grid">"""
    
    for template in templates:
        html += f"""
            <div class="template-card">
                <div class="kind-badge">{template['kind']}</div>
                <div class="template-name">{template['name']}</div>
                <div class="template-file">{template['file']}</div>
            </div>"""
    
    html += """
        </div>
    </div>
</body>
</html>
    """
    
    return html


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_previewer.py <chart_path> [--html output.html]")
        sys.exit(1)
    
    chart_path = sys.argv[1]
    
    try:
        parser = SimpleChartParser()
        chart_data = parser.parse_chart(chart_path)
        
        if '--html' in sys.argv:
            html_idx = sys.argv.index('--html')
            if html_idx + 1 < len(sys.argv):
                output_file = sys.argv[html_idx + 1]
                html_content = generate_simple_html(chart_data)
                with open(output_file, 'w') as f:
                    f.write(html_content)
                print(f"HTML report saved to: {output_file}")
            else:
                print("Error: --html requires output filename")
        else:
            # Print text analysis
            text_output = simple_visualize_text(chart_data)
            print(text_output)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
