"""
Chart Visualizer - Generate visualizations for Helm chart structure using FastAPI
"""

import json
import asyncio
from typing import Dict, List, Any
import networkx as nx
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

from .chart_parser import ChartData, HelmResource


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
    
    async def generate_interactive_html(self, chart_data: ChartData) -> str:
        """Generate interactive HTML visualization"""
        
        # Create network graph
        G = await self._create_network_graph(chart_data)
        
        # Generate Plotly network visualization
        network_fig = await self._create_plotly_network(G, chart_data)
        
        # Generate summary statistics
        stats_fig = await self._create_stats_visualization(chart_data)
        
        # Create combined dashboard
        html_content = await self._create_dashboard_html(network_fig, stats_fig, chart_data)
        
        return html_content
    
    async def generate_network_data(self, chart_data: ChartData) -> Dict[str, Any]:
        """Generate network data for frontend visualization"""
        
        nodes = []
        edges = []
        
        # Add nodes for each resource
        for resource in chart_data.resources:
            nodes.append({
                'id': f"{resource.kind}:{resource.name}",
                'label': resource.name,
                'group': resource.kind,
                'color': self.color_mapping.get(resource.kind, self.color_mapping['Unknown']),
                'size': self._calculate_node_size(resource),
                'metadata': {
                    'kind': resource.kind,
                    'name': resource.name,
                    'namespace': resource.namespace,
                    'api_version': resource.api_version,
                    'labels': resource.labels,
                    'annotations': resource.annotations
                }
            })
        
        # Add edges for relationships
        for relationship in chart_data.relationships:
            source_id = f"{relationship['source']['kind']}:{relationship['source']['name']}"
            target_id = f"{relationship['target']['kind']}:{relationship['target']['name']}"
            
            edges.append({
                'id': f"{source_id}->{target_id}",
                'source': source_id,
                'target': target_id,
                'label': relationship['type'],
                'type': relationship['type']
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'summary': chart_data.summary
        }
    
    def _calculate_node_size(self, resource: HelmResource) -> int:
        """Calculate node size based on resource importance"""
        size_mapping = {
            'Deployment': 50,
            'StatefulSet': 50,
            'Service': 40,
            'Ingress': 45,
            'ConfigMap': 30,
            'Secret': 30,
            'Job': 35,
            'CronJob': 35,
        }
        return size_mapping.get(resource.kind, 25)
    
    async def _create_network_graph(self, chart_data: ChartData) -> nx.Graph:
        """Create NetworkX graph from chart data"""
        G = nx.Graph()
        
        # Add nodes
        for resource in chart_data.resources:
            node_id = f"{resource.kind}:{resource.name}"
            G.add_node(
                node_id,
                kind=resource.kind,
                name=resource.name,
                namespace=resource.namespace,
                color=self.color_mapping.get(resource.kind, self.color_mapping['Unknown'])
            )
        
        # Add edges
        for relationship in chart_data.relationships:
            source_id = f"{relationship['source']['kind']}:{relationship['source']['name']}"
            target_id = f"{relationship['target']['kind']}:{relationship['target']['name']}"
            
            if G.has_node(source_id) and G.has_node(target_id):
                G.add_edge(source_id, target_id, relationship=relationship['type'])
        
        return G
    
    async def _create_plotly_network(self, G: nx.Graph, chart_data: ChartData) -> go.Figure:
        """Create Plotly network visualization"""
        
        # Calculate layout
        pos = nx.spring_layout(G, k=3, iterations=50)
        
        # Extract node information
        node_trace = go.Scatter(
            x=[pos[node][0] for node in G.nodes()],
            y=[pos[node][1] for node in G.nodes()],
            mode='markers+text',
            text=[G.nodes[node]['name'] for node in G.nodes()],
            textposition="middle center",
            marker=dict(
                size=[self._calculate_node_size_from_kind(G.nodes[node]['kind']) for node in G.nodes()],
                color=[G.nodes[node]['color'] for node in G.nodes()],
                line=dict(width=2, color='white')
            ),
            hovertemplate='<b>%{text}</b><br>Kind: %{customdata}<extra></extra>',
            customdata=[G.nodes[node]['kind'] for node in G.nodes()],
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
                line=dict(width=2, color='#888'),
                hoverinfo='none',
                showlegend=False
            )
            edge_traces.append(edge_trace)
        
        # Create figure
        fig = go.Figure(data=[node_trace] + edge_traces)
        
        fig.update_layout(
            title=f"Helm Chart: {chart_data.name}",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=[ dict(
                text="Helm Chart Resource Dependencies",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor='left', yanchor='bottom',
                font=dict(color='#888', size=12)
            )],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white'
        )
        
        return fig
    
    def _calculate_node_size_from_kind(self, kind: str) -> int:
        """Calculate node size for plotting"""
        size_mapping = {
            'Deployment': 30,
            'StatefulSet': 30,
            'Service': 25,
            'Ingress': 28,
            'ConfigMap': 20,
            'Secret': 20,
            'Job': 22,
            'CronJob': 22,
        }
        return size_mapping.get(kind, 15)
    
    async def _create_stats_visualization(self, chart_data: ChartData) -> go.Figure:
        """Create statistics visualization"""
        
        summary = chart_data.summary
        kind_counts = summary.get('kind_counts', {})
        
        # Create pie chart for resource types
        fig = go.Figure(data=[
            go.Pie(
                labels=list(kind_counts.keys()),
                values=list(kind_counts.values()),
                hole=0.3,
                marker_colors=[self.color_mapping.get(kind, self.color_mapping['Unknown']) 
                              for kind in kind_counts.keys()]
            )
        ])
        
        fig.update_layout(
            title="Resource Distribution",
            annotations=[dict(text=f"Total<br>{summary.get('total_resources', 0)}", 
                             x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        
        return fig
    
    async def _create_dashboard_html(self, network_fig: go.Figure, stats_fig: go.Figure, 
                                   chart_data: ChartData) -> str:
        """Create complete HTML dashboard"""
        
        # Convert figures to HTML
        network_html = pyo.plot(network_fig, output_type='div', include_plotlyjs=True)
        stats_html = pyo.plot(stats_fig, output_type='div', include_plotlyjs=False)
        
        # Create metadata table
        metadata_rows = []
        metadata = chart_data.metadata
        metadata_rows.append(f"<tr><td><strong>Name</strong></td><td>{metadata.name}</td></tr>")
        metadata_rows.append(f"<tr><td><strong>Version</strong></td><td>{metadata.version}</td></tr>")
        if metadata.description:
            metadata_rows.append(f"<tr><td><strong>Description</strong></td><td>{metadata.description}</td></tr>")
        metadata_rows.append(f"<tr><td><strong>API Version</strong></td><td>{metadata.api_version}</td></tr>")
        metadata_rows.append(f"<tr><td><strong>Type</strong></td><td>{metadata.type_}</td></tr>")
        
        metadata_table = f"""
        <table class="table table-striped">
            {''.join(metadata_rows)}
        </table>
        """
        
        # Create summary cards
        summary = chart_data.summary
        summary_cards = f"""
        <div class="row mb-3">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">{summary.get('total_resources', 0)}</h5>
                        <p class="card-text">Total Resources</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">{summary.get('resource_types', 0)}</h5>
                        <p class="card-text">Resource Types</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">{summary.get('dependencies_count', 0)}</h5>
                        <p class="card-text">Dependencies</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">{'✓' if summary.get('has_ingress') else '✗'}</h5>
                        <p class="card-text">Has Ingress</p>
                    </div>
                </div>
            </div>
        </div>
        """
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Helm Chart Preview: {chart_data.name}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ 
                    background-color: #f8f9fa; 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }}
                .dashboard-header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 2rem 0;
                    margin-bottom: 2rem;
                }}
                .card {{
                    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
                    border: none;
                }}
                .visualization-container {{
                    background: white;
                    border-radius: 0.375rem;
                    padding: 1rem;
                    margin-bottom: 1rem;
                    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
                }}
            </style>
        </head>
        <body>
            <div class="dashboard-header">
                <div class="container">
                    <h1 class="display-4">Helm Chart Preview</h1>
                    <p class="lead">Interactive visualization of {chart_data.name}</p>
                </div>
            </div>
            
            <div class="container">
                {summary_cards}
                
                <div class="row">
                    <div class="col-lg-8">
                        <div class="visualization-container">
                            <h3>Resource Dependencies</h3>
                            {network_html}
                        </div>
                    </div>
                    <div class="col-lg-4">
                        <div class="visualization-container">
                            <h3>Resource Distribution</h3>
                            {stats_html}
                        </div>
                        
                        <div class="visualization-container">
                            <h3>Chart Metadata</h3>
                            {metadata_table}
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
        
        return html_template
