"""
Chart Visualizer - Generate visualizations for Helm chart structure using FastAPI
"""

from typing import Any

import networkx as nx
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

from .chart_parser import ChartData, HelmResource


class ChartVisualizer:
    """Visualizer for Helm chart structure and relationships"""

    def __init__(self):
        self.color_mapping = {
            # Core workload resources
            "Deployment": "#FF6B6B",
            "StatefulSet": "#FF9FF3",
            "DaemonSet": "#54A0FF",
            "Job": "#5F27CD",
            "CronJob": "#00D2D3",
            "Pod": "#FF8A80",
            # Networking resources
            "Service": "#4ECDC4",
            "Ingress": "#FECA57",
            "NetworkPolicy": "#26A69A",
            # Security & RBAC resources
            "ServiceAccount": "#3742FA",
            "Role": "#2F3542",
            "RoleBinding": "#57606F",
            "ClusterRole": "#1A237E",
            "ClusterRoleBinding": "#303F9F",
            # Storage resources
            "PersistentVolume": "#FF9F43",
            "PersistentVolumeClaim": "#FFA502",
            # Configuration resources
            "ConfigMap": "#45B7D1",
            "Secret": "#96CEB4",
            # Scaling resources
            "HorizontalPodAutoscaler": "#8BC34A",
            "Unknown": "#DDD",
        }

        # Resource categories for better organization
        self.resource_categories = {
            "Workloads": [
                "Deployment",
                "StatefulSet",
                "DaemonSet",
                "Job",
                "CronJob",
                "Pod",
            ],
            "Networking": ["Service", "Ingress", "NetworkPolicy"],
            "Security & RBAC": [
                "ServiceAccount",
                "Role",
                "RoleBinding",
                "ClusterRole",
                "ClusterRoleBinding",
            ],
            "Storage": ["PersistentVolume", "PersistentVolumeClaim"],
            "Configuration": ["ConfigMap", "Secret"],
            "Scaling": ["HorizontalPodAutoscaler"],
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
        html_content = await self._create_dashboard_html(
            network_fig, stats_fig, chart_data
        )

        return html_content

    async def generate_network_data(self, chart_data: ChartData) -> dict[str, Any]:
        """Generate network data for frontend visualization"""

        nodes = []
        edges = []

        # Add nodes for each resource
        for resource in chart_data.resources:
            nodes.append(
                {
                    "id": f"{resource.kind}:{resource.name}",
                    "label": resource.name,
                    "group": resource.kind,
                    "color": self.color_mapping.get(
                        resource.kind, self.color_mapping["Unknown"]
                    ),
                    "size": self._calculate_node_size(resource),
                    "metadata": {
                        "kind": resource.kind,
                        "name": resource.name,
                        "namespace": resource.namespace,
                        "api_version": resource.api_version,
                        "labels": resource.labels,
                        "annotations": resource.annotations,
                    },
                }
            )

        # Add edges for relationships
        for relationship in chart_data.relationships:
            source_id = (
                f"{relationship['source']['kind']}:{relationship['source']['name']}"
            )
            target_id = (
                f"{relationship['target']['kind']}:{relationship['target']['name']}"
            )

            edges.append(
                {
                    "id": f"{source_id}->{target_id}",
                    "source": source_id,
                    "target": target_id,
                    "label": relationship["type"],
                    "type": relationship["type"],
                }
            )

        return {"nodes": nodes, "edges": edges, "summary": chart_data.summary}

    def _calculate_node_size(self, resource: HelmResource) -> int:
        """Calculate node size based on resource importance"""
        size_mapping = {
            # Larger nodes for key components
            "Deployment": 60,
            "StatefulSet": 60,
            "Service": 50,
            "Ingress": 55,
            "ServiceAccount": 45,
            # Medium nodes for supporting resources
            "ConfigMap": 35,
            "Secret": 35,
            "Job": 40,
            "CronJob": 40,
            "PersistentVolumeClaim": 40,
            "Role": 35,
            "RoleBinding": 35,
            # Smaller nodes for less critical resources
            "Pod": 30,
            "NetworkPolicy": 30,
            "HorizontalPodAutoscaler": 30,
        }
        return size_mapping.get(resource.kind, 25)

    async def _create_network_graph(self, chart_data: ChartData) -> nx.Graph:
        """Create NetworkX graph from chart data"""
        G = nx.Graph()

        # Check if we have resources
        if not chart_data.resources:
            print("Warning: No resources found in chart data")
            return G

        # Add nodes
        for resource in chart_data.resources:
            node_id = f"{resource.kind}:{resource.name}"
            G.add_node(
                node_id,
                kind=resource.kind,
                name=resource.name,
                namespace=resource.namespace,
                color=self.color_mapping.get(
                    resource.kind, self.color_mapping["Unknown"]
                ),
            )

        # Add edges
        for relationship in chart_data.relationships:
            source_id = (
                f"{relationship['source']['kind']}:{relationship['source']['name']}"
            )
            target_id = (
                f"{relationship['target']['kind']}:{relationship['target']['name']}"
            )

            if G.has_node(source_id) and G.has_node(target_id):
                G.add_edge(source_id, target_id, relationship=relationship["type"])

        return G

    async def _create_plotly_network(
        self, G: nx.Graph, chart_data: ChartData
    ) -> go.Figure:
        """Create Plotly network visualization"""

        # Handle empty graph
        if len(G.nodes()) == 0:
            fig = go.Figure()
            fig.add_annotation(
                text="No resources found in the chart",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                xanchor="center",
                yanchor="middle",
                showarrow=False,
                font={"size": 16, "color": "gray"},
            )
            fig.update_layout(
                title="Helm Chart Network - No Resources",
                showlegend=False,
                xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
                yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            )
            return fig

        # Calculate layout with better positioning for key components
        pos = self._calculate_strategic_layout(G)

        # Group nodes by category for better visualization
        node_groups = self._group_nodes_by_category(G)

        # Create traces for different resource types
        traces = []

        # Create traces for each category
        for category, nodes in node_groups.items():
            if not nodes:
                continue

            node_data = [G.nodes[node] for node in nodes]

            node_trace = go.Scatter(
                x=[pos[node][0] for node in nodes],
                y=[pos[node][1] for node in nodes],
                mode="markers+text",
                text=[data["name"] for data in node_data],
                textposition="middle center",
                textfont={"size": 10, "color": "white"},
                marker={
                    "size": [
                        self._calculate_node_size_from_kind(data["kind"])
                        for data in node_data
                    ],
                    "color": [data["color"] for data in node_data],
                    "line": {"width": 2, "color": "white"},
                    "symbol": "circle",
                },
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Kind: %{customdata[0]}<br>"
                    "Category: %{customdata[1]}<extra></extra>"
                ),
                customdata=[[data["kind"], category] for data in node_data],
                name=f"{category} ({len(nodes)})",
                showlegend=True,
            )
            traces.append(node_trace)

        # Create edge traces
        edge_traces = self._create_edge_traces(G, pos)

        # Create figure
        fig = go.Figure(data=traces + edge_traces)

        fig.update_layout(
            title={
                "text": f"Helm Chart Architecture: {chart_data.name}",
                "x": 0.5,
                "font": {"size": 20},
            },
            showlegend=True,
            legend={
                "orientation": "v",
                "yanchor": "top",
                "y": 1,
                "xanchor": "left",
                "x": 1.01,
            },
            hovermode="closest",
            margin={"b": 20, "l": 5, "r": 5, "t": 60},
            annotations=[
                {
                    "text": "Interactive Kubernetes Resource Dependencies",
                    "showarrow": False,
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.005,
                    "y": -0.002,
                    "xanchor": "left",
                    "yanchor": "bottom",
                    "font": {"color": "#888", "size": 12},
                },
                # Add category labels
                {
                    "text": (
                        "📊 Key Components: ServiceAccount → "
                        "Deployment → Service → Ingress"
                    ),
                    "showarrow": False,
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 1.05,
                    "xanchor": "center",
                    "yanchor": "bottom",
                    "font": {"color": "#555", "size": 14},
                },
            ],
            xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            plot_bgcolor="white",
            width=1000,
            height=700,
        )

        return fig

    def _calculate_node_size_from_kind(self, kind: str) -> int:
        """Calculate node size for plotting"""
        size_mapping = {
            # Key components - larger sizes
            "Deployment": 40,
            "StatefulSet": 40,
            "Service": 35,
            "Ingress": 38,
            "ServiceAccount": 32,
            # Supporting components - medium sizes
            "ConfigMap": 25,
            "Secret": 25,
            "Job": 28,
            "CronJob": 28,
            "PersistentVolumeClaim": 28,
            "Role": 25,
            "RoleBinding": 25,
            # Other components - smaller sizes
            "Pod": 20,
            "NetworkPolicy": 22,
            "HorizontalPodAutoscaler": 22,
        }
        return size_mapping.get(kind, 18)

    def _calculate_strategic_layout(self, G: nx.Graph) -> dict:
        """Calculate strategic layout positioning key components prominently"""
        # Use spring layout as base
        pos = nx.spring_layout(G, k=4, iterations=100)

        # Get key component nodes
        key_components = ["ServiceAccount", "Deployment", "Service", "Ingress"]
        key_nodes = [
            node for node in G.nodes() if G.nodes[node]["kind"] in key_components
        ]

        if key_nodes:
            # Arrange key components in a horizontal line at the top
            for _i, node in enumerate(key_nodes):
                if G.nodes[node]["kind"] == "ServiceAccount":
                    pos[node] = (-1.5, 1.0)
                elif G.nodes[node]["kind"] == "Deployment":
                    pos[node] = (-0.5, 1.0)
                elif G.nodes[node]["kind"] == "Service":
                    pos[node] = (0.5, 1.0)
                elif G.nodes[node]["kind"] == "Ingress":
                    pos[node] = (1.5, 1.0)

        return pos

    def _group_nodes_by_category(self, G: nx.Graph) -> dict[str, list]:
        """Group nodes by resource category"""
        node_groups = {}

        for category, kinds in self.resource_categories.items():
            nodes = [node for node in G.nodes() if G.nodes[node]["kind"] in kinds]
            if nodes:
                node_groups[category] = nodes

        # Add uncategorized nodes
        categorized_kinds = set()
        for kinds in self.resource_categories.values():
            categorized_kinds.update(kinds)

        uncategorized = [
            node for node in G.nodes() if G.nodes[node]["kind"] not in categorized_kinds
        ]
        if uncategorized:
            node_groups["Other"] = uncategorized

        return node_groups

    def _create_edge_traces(self, G: nx.Graph, pos: dict) -> list:
        """Create edge traces with different styles based on relationship type"""
        edge_traces = []

        for edge in G.edges(data=True):
            source, target, data = edge
            x0, y0 = pos[source]
            x1, y1 = pos[target]

            # Determine edge style based on relationship type
            relationship_type = data.get("relationship", "default")

            if relationship_type == "exposes":
                line_color = "#4ECDC4"
                line_width = 3
                line_dash = "solid"
            elif relationship_type == "routes_to":
                line_color = "#FECA57"
                line_width = 3
                line_dash = "solid"
            elif relationship_type == "uses":
                line_color = "#96CEB4"
                line_width = 2
                line_dash = "dash"
            else:
                line_color = "#888"
                line_width = 2
                line_dash = "solid"

            edge_trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line={"width": line_width, "color": line_color, "dash": line_dash},
                hovertemplate=(
                    f"<b>{relationship_type}</b><br>"
                    f"{G.nodes[source]['name']} → "
                    f"{G.nodes[target]['name']}<extra></extra>"
                ),
                showlegend=False,
            )
            edge_traces.append(edge_trace)

        return edge_traces

    def _analyze_key_components(
        self, chart_data: ChartData
    ) -> dict[str, dict[str, str]]:
        """Analyze the status of key components in the chart"""
        kind_counts = chart_data.summary.get("kind_counts", {})

        def get_component_status(kind: str) -> dict[str, str]:
            count = kind_counts.get(kind, 0)
            if count > 0:
                return {"count": count, "icon": "✅", "class": "border-success"}
            else:
                return {"count": 0, "icon": "❌", "class": "border-danger"}

        return {
            "serviceaccount": get_component_status("ServiceAccount"),
            "deployment": get_component_status("Deployment"),
            "service": get_component_status("Service"),
            "ingress": get_component_status("Ingress"),
        }

    def _get_security_class(self, score: int) -> str:
        """Get CSS class for security score"""
        if score >= 80:
            return "security-high"
        elif score >= 50:
            return "security-medium"
        else:
            return "security-low"

    def _get_security_recommendations(self, summary: dict[str, Any]) -> str:
        """Get security recommendations based on summary"""
        score = summary.get("security_score", 0)
        if score >= 80:
            return "Excellent security configuration!"
        elif score >= 50:
            return "Good security, consider adding missing components."
        else:
            recommendations = []
            if not summary.get("has_service_accounts"):
                recommendations.append("Add ServiceAccounts")
            if not summary.get("has_rbac"):
                recommendations.append("Implement RBAC")
            if not summary.get("has_secrets"):
                recommendations.append("Use Secrets for sensitive data")
            return f"Improve security by: {', '.join(recommendations)}"

    async def _create_stats_visualization(self, chart_data: ChartData) -> go.Figure:
        """Create enhanced statistics visualization highlighting key components"""

        summary = chart_data.summary
        kind_counts = summary.get("kind_counts", {})

        # Separate key components from others
        key_components = ["ServiceAccount", "Deployment", "Service", "Ingress"]
        key_counts = {
            k: kind_counts.get(k, 0)
            for k in key_components
            if kind_counts.get(k, 0) > 0
        }

        # Create subplots
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Key Components",
                "All Resource Types",
                "Resource Categories",
                "Architecture Flow",
            ),
            specs=[
                [{"type": "pie"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "scatter"}],
            ],
        )

        # Key components pie chart
        if key_counts:
            fig.add_trace(
                go.Pie(
                    labels=list(key_counts.keys()),
                    values=list(key_counts.values()),
                    hole=0.4,
                    marker_colors=[
                        self.color_mapping.get(kind, self.color_mapping["Unknown"])
                        for kind in key_counts.keys()
                    ],
                    name="Key Components",
                ),
                row=1,
                col=1,
            )

        # All resources pie chart
        fig.add_trace(
            go.Pie(
                labels=list(kind_counts.keys()),
                values=list(kind_counts.values()),
                hole=0.3,
                marker_colors=[
                    self.color_mapping.get(kind, self.color_mapping["Unknown"])
                    for kind in kind_counts.keys()
                ],
                name="All Resources",
            ),
            row=1,
            col=2,
        )

        # Resource categories bar chart
        category_counts = {}
        for category, kinds in self.resource_categories.items():
            count = sum(kind_counts.get(kind, 0) for kind in kinds)
            if count > 0:
                category_counts[category] = count

        if category_counts:
            fig.add_trace(
                go.Bar(
                    x=list(category_counts.keys()),
                    y=list(category_counts.values()),
                    marker_color=[
                        "#667eea",
                        "#764ba2",
                        "#f093fb",
                        "#f5576c",
                        "#4facfe",
                        "#00f2fe",
                    ],
                    name="Categories",
                ),
                row=2,
                col=1,
            )

        # Architecture flow diagram (simplified)
        flow_x = [1, 2, 3, 4]
        flow_y = [1, 1, 1, 1]
        flow_labels = ["ServiceAccount", "Deployment", "Service", "Ingress"]
        flow_sizes = [key_counts.get(label, 0) * 20 + 20 for label in flow_labels]

        fig.add_trace(
            go.Scatter(
                x=flow_x,
                y=flow_y,
                mode="markers+text",
                text=flow_labels,
                textposition="bottom center",
                marker={
                    "size": flow_sizes,
                    "color": [
                        self.color_mapping.get(label, "#ccc") for label in flow_labels
                    ],
                    "line": {"width": 2, "color": "white"},
                },
                name="Flow",
            ),
            row=2,
            col=2,
        )

        # Add flow arrows
        for i in range(len(flow_x) - 1):
            fig.add_annotation(
                x=flow_x[i + 1],
                y=flow_y[i + 1],
                ax=flow_x[i],
                ay=flow_y[i],
                xref=f"x{4}",
                yref=f"y{4}",
                axref=f"x{4}",
                ayref=f"y{4}",
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="#666",
            )

        fig.update_layout(
            title="Helm Chart Analytics Dashboard", showlegend=False, height=800
        )

        return fig

    async def _create_dashboard_html(
        self, network_fig: go.Figure, stats_fig: go.Figure, chart_data: ChartData
    ) -> str:
        """Create complete HTML dashboard"""

        try:
            # Convert figures to HTML with proper JavaScript inclusion
            network_html = pyo.plot(
                network_fig,
                output_type="div",
                include_plotlyjs=True,
                config={"displayModeBar": True, "responsive": True},
            )
            stats_html = pyo.plot(
                stats_fig,
                output_type="div",
                include_plotlyjs="inline",
                config={"displayModeBar": True, "responsive": True},
            )
        except Exception as e:
            print(f"Warning: Failed to generate plots: {e}")
            network_html = "<div class='alert alert-warning'>Network visualization failed to load</div>"
            stats_html = "<div class='alert alert-warning'>Statistics visualization failed to load</div>"

        # Create metadata table
        metadata_rows = []
        metadata = chart_data.metadata
        metadata_rows.append(
            f"<tr><td><strong>Name</strong></td><td>{metadata.name}</td></tr>"
        )
        metadata_rows.append(
            f"<tr><td><strong>Version</strong></td><td>{metadata.version}</td></tr>"
        )
        if metadata.description:
            metadata_rows.append(
                f"<tr><td><strong>Description</strong></td><td>{metadata.description}</td></tr>"
            )
        metadata_rows.append(
            f"<tr><td><strong>API Version</strong></td>"
            f"<td>{metadata.api_version}</td></tr>"
        )
        metadata_rows.append(
            f"<tr><td><strong>Type</strong></td><td>{metadata.type_}</td></tr>"
        )

        metadata_table = f"""
        <table class="table table-striped">
            {"".join(metadata_rows)}
        </table>
        """

        # Create summary cards with key component highlights
        summary = chart_data.summary
        key_components_status = self._analyze_key_components(chart_data)

        summary_cards = f"""
        <div class="row mb-4">
            <div class="col-md-12">
                <h4 class="mb-3">🏗️ Architecture Overview</h4>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-3">
                <div class="card text-center border-primary">
                    <div class="card-body">
                        <h5 class="card-title text-primary">
                            {summary.get("total_resources", 0)}
                        </h5>
                        <p class="card-text">Total Resources</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center border-info">
                    <div class="card-body">
                        <h5 class="card-title text-info">{summary.get("resource_types", 0)}</h5>
                        <p class="card-text">Resource Types</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center border-warning">
                    <div class="card-body">
                        <h5 class="card-title text-warning">{summary.get("dependencies_count", 0)}</h5>
                        <p class="card-text">Dependencies</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center border-success">
                    <div class="card-body">
                        <h5 class="card-title text-success">{"✓" if summary.get("has_ingress") else "✗"}</h5>
                        <p class="card-text">Has Ingress</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-3">
            <div class="col-md-12">
                <h5 class="mb-3">🔑 Key Components Status</h5>
            </div>
        </div>
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card text-center {key_components_status["serviceaccount"]["class"]}">
                    <div class="card-body">
                        <h5 class="card-title">{key_components_status["serviceaccount"]["icon"]}</h5>
                        <p class="card-text">ServiceAccount</p>
                        <small class="text-muted">{key_components_status["serviceaccount"]["count"]} found</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center {key_components_status["deployment"]["class"]}">
                    <div class="card-body">
                        <h5 class="card-title">{key_components_status["deployment"]["icon"]}</h5>
                        <p class="card-text">Deployment</p>
                        <small class="text-muted">{key_components_status["deployment"]["count"]} found</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center {key_components_status["service"]["class"]}">
                    <div class="card-body">
                        <h5 class="card-title">{key_components_status["service"]["icon"]}</h5>
                        <p class="card-text">Service</p>
                        <small class="text-muted">{key_components_status["service"]["count"]} found</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center {key_components_status["ingress"]["class"]}">
                    <div class="card-body">
                        <h5 class="card-title">{key_components_status["ingress"]["icon"]}</h5>
                        <p class="card-text">Ingress</p>
                        <small class="text-muted">{key_components_status["ingress"]["count"]} found</small>
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
            <title>Helm Chart Architecture: {chart_data.name}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
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
                    transition: transform 0.2s ease-in-out;
                }}
                .card:hover {{
                    transform: translateY(-2px);
                }}
                .visualization-container {{
                    background: white;
                    border-radius: 0.375rem;
                    padding: 1.5rem;
                    margin-bottom: 1.5rem;
                    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
                }}
                .architecture-score {{
                    font-size: 2rem;
                    font-weight: bold;
                }}
                .component-flow {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 1rem 0;
                }}
                .component-arrow {{
                    margin: 0 1rem;
                    color: #6c757d;
                }}
                .badge-large {{
                    font-size: 1rem;
                    padding: 0.5rem 1rem;
                }}
                .security-indicator {{
                    text-align: center;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    margin: 0.5rem 0;
                }}
                .security-high {{ background-color: #d4edda; color: #155724; }}
                .security-medium {{ background-color: #fff3cd; color: #856404; }}
                .security-low {{ background-color: #f8d7da; color: #721c24; }}
            </style>
        </head>
        <body>
            <div class="dashboard-header">
                <div class="container">
                    <h1 class="display-4"><i class="fas fa-cubes"></i> Helm Chart Architecture</h1>
                    <p class="lead">Interactive visualization and analysis of <strong>{chart_data.name}</strong></p>
                    <div class="row mt-3">
                        <div class="col-md-4">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-award me-2"></i>
                                <span>Architecture Grade: <strong>{summary.get("architecture_grade", "Unknown")}</strong></span>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-shield-alt me-2"></i>
                                <span>Security Score: <strong>{summary.get("security_score", 0)}/100</strong></span>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-layer-group me-2"></i>
                                <span>Total Resources: <strong>{summary.get("total_resources", 0)}</strong></span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="container">
                {summary_cards}

                <div class="row mb-4">
                    <div class="col-md-12">
                        <div class="visualization-container">
                            <h5 class="mb-3"><i class="fas fa-route"></i> Typical Kubernetes Architecture Flow</h5>
                            <div class="component-flow">
                                <span class="badge bg-primary badge-large">👤 User</span>
                                <i class="fas fa-arrow-right component-arrow"></i>
                                <span class="badge bg-warning badge-large">🌐 Ingress</span>
                                <i class="fas fa-arrow-right component-arrow"></i>
                                <span class="badge bg-info badge-large">🔗 Service</span>
                                <i class="fas fa-arrow-right component-arrow"></i>
                                <span class="badge bg-danger badge-large">🚀 Deployment</span>
                                <i class="fas fa-arrow-right component-arrow"></i>
                                <span class="badge bg-secondary badge-large">🔐 ServiceAccount</span>
                            </div>
                            <p class="text-muted text-center mt-2">
                                <small>This chart implements {summary.get("architecture_score", 0)}% of the complete architecture pattern</small>
                            </p>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-lg-12">
                        <div class="visualization-container">
                            <h3><i class="fas fa-project-diagram"></i> Resource Dependencies</h3>
                            <p class="text-muted">Interactive network showing relationships between Kubernetes resources</p>
                            {network_html}
                        </div>
                    </div>
                </div>

                <div class="row mt-4">
                    <div class="col-lg-6">
                        <div class="visualization-container">
                            <h3><i class="fas fa-chart-pie"></i> Resource Analytics</h3>
                            {stats_html}
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="visualization-container">
                            <h3><i class="fas fa-info-circle"></i> Chart Metadata</h3>
                            {metadata_table}
                        </div>

                        <div class="visualization-container">
                            <h3><i class="fas fa-shield-alt"></i> Security Assessment</h3>
                            <div class="security-indicator {self._get_security_class(summary.get("security_score", 0))}">
                                <strong>Security Score: {summary.get("security_score", 0)}/100</strong>
                                <br>
                                <small>{self._get_security_recommendations(summary)}</small>
                            </div>
                            <ul class="list-unstyled mt-3">
                                <li><i class="fas fa-{"check text-success" if summary.get("has_service_accounts") else "times text-danger"}"></i> ServiceAccounts</li>
                                <li><i class="fas fa-{"check text-success" if summary.get("has_rbac") else "times text-danger"}"></i> RBAC (Roles/RoleBindings)</li>
                                <li><i class="fas fa-{"check text-success" if summary.get("has_secrets") else "times text-danger"}"></i> Secrets Management</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="row mt-4">
                    <div class="col-md-12">
                        <div class="visualization-container">
                            <h3><i class="fas fa-layer-group"></i> Resource Categories</h3>
                            <div class="row">
                                <div class="col-md-2">
                                    <div class="text-center">
                                        <h4 class="text-primary">{summary.get("workload_resources", 0)}</h4>
                                        <p>Workloads</p>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="text-center">
                                        <h4 class="text-info">{summary.get("networking_resources", 0)}</h4>
                                        <p>Networking</p>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="text-center">
                                        <h4 class="text-warning">{summary.get("storage_resources", 0)}</h4>
                                        <p>Storage</p>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="text-center">
                                        <h4 class="text-success">{summary.get("config_resources", 0)}</h4>
                                        <p>Configuration</p>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="text-center">
                                        <h4 class="text-secondary">{summary.get("security_resources", 0)}</h4>
                                        <p>Security</p>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="text-center">
                                        <h4 class="text-dark">{summary.get("dependencies_count", 0)}</h4>
                                        <p>Dependencies</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """

        return html_template
