"""
Chart Visualizer - Generate visualizations for Helm chart structure
"""

import json
import networkx as nx
from typing import Dict, List, Any
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots


class ChartVisualizer:
    """Visualizer for Helm chart structure and relationships"""
    
    def __init__(self):
        self.color_mapping = {
            'Deployment': '#FF6B6B',
            'Service': '#4ECDC4',
            'ConfigMap': '#45B7D1',
            'Secret': '#96CEB4',
            'Ingress': '#FECA57',
            'StatefulSet': '#FF9FF3',
            'DaemonSet': '#54A0FF',
            'Job': '#5F27CD',
            'CronJob': '#00D2D3',
            'PersistentVolume': '#FF9F43',
            'PersistentVolumeClaim': '#FFA502',
            'ServiceAccount': '#3742FA',
            'Role': '#2F3542',
            'RoleBinding': '#57606F',
            'Unknown': '#DDD'
        }
    
    def generate_interactive_html(self, chart_data: Dict[str, Any]) -> str:
        """Generate interactive HTML visualization"""
        
        # Create network graph
        G = self._create_network_graph(chart_data)
        
        # Generate Plotly network visualization
        network_fig = self._create_plotly_network(G, chart_data)
        
        # Generate summary statistics
        stats_fig = self._create_stats_visualization(chart_data)
        
        # Create combined dashboard
        html_content = self._create_dashboard_html(network_fig, stats_fig, chart_data)
        
        return html_content
    
    def _create_network_graph(self, chart_data: Dict[str, Any]) -> nx.DiGraph:
        """Create NetworkX graph from chart data"""
        G = nx.DiGraph()
        
        # Add nodes for each template
        for template in chart_data.get('templates', []):
            node_id = f"{template['kind']}/{template['name']}"
            G.add_node(node_id, 
                      kind=template['kind'],
                      name=template['name'],
                      file=template['file'],
                      color=self.color_mapping.get(template['kind'], '#DDD'))
        
        # Add edges for relationships
        for rel in chart_data.get('relationships', []):
            source_id = f"{rel['source_kind']}/{rel['source']}"
            target_id = f"{rel['target_kind']}/{rel['target']}"
            
            # Only add edge if both nodes exist
            if G.has_node(source_id) and G.has_node(target_id):
                G.add_edge(source_id, target_id, 
                          relationship=rel['relationship_type'],
                          field=rel['field'])
        
        return G
    
    def _create_plotly_network(self, G: nx.DiGraph, chart_data: Dict[str, Any]) -> go.Figure:
        """Create Plotly network visualization"""
        
        if len(G.nodes()) == 0:
            # Create empty plot if no nodes
            fig = go.Figure()
            fig.add_annotation(
                text="No templates found in chart",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font_size=16
            )
            return fig
        
        # Use spring layout for positioning
        pos = nx.spring_layout(G, k=3, iterations=50)
        
        # Extract node information
        node_trace = go.Scatter(
            x=[pos[node][0] for node in G.nodes()],
            y=[pos[node][1] for node in G.nodes()],
            mode='markers+text',
            text=[f"{G.nodes[node]['kind']}<br>{G.nodes[node]['name']}" for node in G.nodes()],
            textposition="middle center",
            textfont=dict(size=10),
            marker=dict(
                size=30,
                color=[G.nodes[node]['color'] for node in G.nodes()],
                line=dict(width=2, color='black')
            ),
            hoverinfo='text',
            hovertext=[f"Kind: {G.nodes[node]['kind']}<br>"
                      f"Name: {G.nodes[node]['name']}<br>"
                      f"File: {G.nodes[node]['file']}" for node in G.nodes()],
            name="Resources"
        )
        
        # Extract edge information
        edge_traces = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            edge_trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode='lines',
                line=dict(width=2, color='gray'),
                hoverinfo='none',
                showlegend=False
            )
            edge_traces.append(edge_trace)
        
        # Create figure
        fig = go.Figure(data=[node_trace] + edge_traces)
        
        fig.update_layout(
            title=f"Helm Chart Structure: {chart_data.get('name', 'Unknown')}",
            titlefont_size=16,
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=[ dict(
                text="Hover over nodes for details",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor='left', yanchor='bottom',
                font=dict(color="gray", size=12)
            )],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white'
        )
        
        return fig
    
    def _create_stats_visualization(self, chart_data: Dict[str, Any]) -> go.Figure:
        """Create statistics visualization"""
        
        templates = chart_data.get('templates', [])
        
        # Count resources by kind
        kind_counts = {}
        for template in templates:
            kind = template['kind']
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Resource Types', 'Dependencies', 'Template Variables', 'Chart Info'),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "table"}]]
        )
        
        # Resource types pie chart
        if kind_counts:
            fig.add_trace(
                go.Pie(
                    labels=list(kind_counts.keys()),
                    values=list(kind_counts.values()),
                    marker_colors=[self.color_mapping.get(k, '#DDD') for k in kind_counts.keys()]
                ),
                row=1, col=1
            )
        
        # Dependencies bar chart
        dependencies = chart_data.get('dependencies', [])
        if dependencies:
            dep_names = [dep.get('name', 'Unknown') for dep in dependencies]
            dep_versions = [dep.get('version', '1.0.0') for dep in dependencies]
            fig.add_trace(
                go.Bar(x=dep_names, y=[1]*len(dep_names), name='Dependencies'),
                row=1, col=2
            )
        
        # Template variables analysis
        all_vars = []
        for template in templates:
            all_vars.extend(template.get('template_variables', []))
        
        # Count most common variables
        var_counts = {}
        for var in all_vars:
            var_counts[var] = var_counts.get(var, 0) + 1
        
        # Show top 10 variables
        sorted_vars = sorted(var_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        if sorted_vars:
            fig.add_trace(
                go.Bar(
                    x=[var[0] for var in sorted_vars],
                    y=[var[1] for var in sorted_vars],
                    name='Variable Usage'
                ),
                row=2, col=1
            )
        
        # Chart info table
        chart_info = [
            ['Chart Name', chart_data.get('name', 'Unknown')],
            ['Version', chart_data.get('version', 'Unknown')],
            ['Templates', str(len(templates))],
            ['Dependencies', str(len(dependencies))],
            ['Relationships', str(len(chart_data.get('relationships', [])))]
        ]
        
        fig.add_trace(
            go.Table(
                header=dict(values=['Property', 'Value'], fill_color='lightblue'),
                cells=dict(values=[[row[0] for row in chart_info], 
                                  [row[1] for row in chart_info]],
                          fill_color='white')
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=800,
            title_text=f"Chart Analysis: {chart_data.get('name', 'Unknown')}",
            showlegend=False
        )
        
        return fig
    
    def _create_dashboard_html(self, network_fig: go.Figure, stats_fig: go.Figure, 
                             chart_data: Dict[str, Any]) -> str:
        """Create complete HTML dashboard"""
        
        # Convert figures to HTML
        network_html = pyo.plot(network_fig, output_type='div', include_plotlyjs=False)
        stats_html = pyo.plot(stats_fig, output_type='div', include_plotlyjs=False)
        
        # Create template data summary
        templates_info = []
        for template in chart_data.get('templates', []):
            templates_info.append({
                'name': template['name'],
                'kind': template['kind'],
                'file': template['file'],
                'variables': len(template.get('template_variables', []))
            })
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Helm Chart Previewer: {chart_data.get('name', 'Unknown')}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }}
        .chart-info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .templates-list {{
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
        }}
        .template-item {{
            background: white;
            padding: 10px;
            margin: 5px 0;
            border-left: 4px solid #007bff;
            border-radius: 3px;
        }}
        .visualization-section {{
            margin: 20px 0;
        }}
        .section-title {{
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Helm Chart Previewer</h1>
            <h2>{chart_data.get('name', 'Unknown Chart')} v{chart_data.get('version', '1.0.0')}</h2>
            <p>{chart_data.get('description', 'No description available')}</p>
        </div>
        
        <div class="chart-info">
            <h3>Chart Information</h3>
            <p><strong>Path:</strong> {chart_data.get('path', 'Unknown')}</p>
            <p><strong>Templates:</strong> {len(chart_data.get('templates', []))}</p>
            <p><strong>Dependencies:</strong> {len(chart_data.get('dependencies', []))}</p>
            <p><strong>Relationships:</strong> {len(chart_data.get('relationships', []))}</p>
        </div>
        
        <div class="visualization-section">
            <div class="section-title">Chart Structure</div>
            {network_html}
        </div>
        
        <div class="visualization-section">
            <div class="section-title">Detailed Analysis</div>
            {stats_html}
        </div>
        
        <div class="templates-list">
            <div class="section-title">Templates</div>
            {"".join([f'''
            <div class="template-item">
                <strong>{t["name"]}</strong> ({t["kind"]}) - {t["file"]}<br>
                <small>Template Variables: {t["variables"]}</small>
            </div>
            ''' for t in templates_info])}
        </div>
    </div>
</body>
</html>
        """
        
        return html_template
    
    def generate_static_visualization(self, chart_data: Dict[str, Any], 
                                    output_path: str, format: str = 'png'):
        """Generate static visualization file"""
        
        G = self._create_network_graph(chart_data)
        fig = self._create_plotly_network(G, chart_data)
        
        # Save in specified format
        if format == 'png':
            fig.write_image(output_path, width=1200, height=800)
        elif format == 'svg':
            fig.write_image(output_path, format='svg', width=1200, height=800)
        elif format == 'pdf':
            fig.write_image(output_path, format='pdf', width=1200, height=800)
        else:
            raise ValueError(f"Unsupported format: {format}")
