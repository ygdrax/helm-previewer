"""
CLI Application using Typer for Helm Chart Previewer
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint

from .chart_parser import HelmChartParser
from .visualizer import ChartVisualizer

app = typer.Typer(
    name="helm-previewer",
    help="Helm Chart Previewer - Visualize Helm chart structure and dependencies",
    add_completion=False
)

console = Console()


@app.command()
def parse(
    chart_path: str = typer.Argument(..., help="Path to Helm chart directory"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for visualization"),
    format: str = typer.Option("html", "--format", "-f", help="Output format (html, json)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Parse a Helm chart and generate visualization"""
    
    async def _parse_chart():
        chart_path_obj = Path(chart_path)
        
        if not chart_path_obj.exists():
            console.print(f"[red]Error: Chart path does not exist: {chart_path}[/red]")
            raise typer.Exit(1)
        
        if not chart_path_obj.is_dir():
            console.print(f"[red]Error: Chart path must be a directory: {chart_path}[/red]")
            raise typer.Exit(1)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Parse chart
            task = progress.add_task("Parsing Helm chart...", total=None)
            parser = HelmChartParser()
            chart_data = await parser.parse_chart(chart_path)
            progress.remove_task(task)
            
            # Display summary
            _display_chart_summary(chart_data, verbose)
            
            # Generate output if requested
            if output:
                task = progress.add_task(f"Generating {format} output...", total=None)
                
                if format.lower() == "html":
                    visualizer = ChartVisualizer()
                    html_content = await visualizer.generate_interactive_html(chart_data)
                    
                    with open(output, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    console.print(f"[green]✓ HTML visualization saved to: {output}[/green]")
                
                elif format.lower() == "json":
                    import json
                    
                    # Convert to JSON-serializable format
                    chart_dict = chart_data.model_dump()
                    
                    with open(output, 'w', encoding='utf-8') as f:
                        json.dump(chart_dict, f, indent=2, default=str)
                    
                    console.print(f"[green]✓ JSON data saved to: {output}[/green]")
                
                else:
                    console.print(f"[red]Error: Unsupported format: {format}[/red]")
                    raise typer.Exit(1)
                
                progress.remove_task(task)
    
    try:
        asyncio.run(_parse_chart())
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("localhost", "--host", help="Host to bind to"),
    port: int = typer.Option(8080, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes")
):
    """Start the web server"""
    
    try:
        import uvicorn
        from .app import app as fastapi_app
        
        console.print(f"[blue]Starting Helm Chart Previewer web server...[/blue]")
        console.print(f"[blue]Server will be available at: http://{host}:{port}[/blue]")
        console.print(f"[blue]API documentation at: http://{host}:{port}/api/docs[/blue]")
        
        if reload:
            console.print("[yellow]Running in development mode with auto-reload[/yellow]")
        
        uvicorn.run(
            "helm_previewer.app:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,
            log_level="info"
        )
        
    except ImportError:
        console.print("[red]Error: uvicorn not found. Please install with: uv add uvicorn[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
        raise typer.Exit(0)


@app.command()
def create_test_chart(
    name: str = typer.Argument("test-chart", help="Name of the test chart to create"),
    path: Optional[str] = typer.Option(None, "--path", help="Path where to create the chart")
):
    """Create a test Helm chart for demonstration"""
    
    import subprocess
    
    try:
        chart_path = Path(path) if path else Path.cwd()
        target_path = chart_path / name
        
        if target_path.exists():
            if not typer.confirm(f"Chart directory {target_path} already exists. Overwrite?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit(0)
            
            import shutil
            shutil.rmtree(target_path)
        
        console.print(f"[blue]Creating test chart: {name}[/blue]")
        
        # Try to use helm create command
        result = subprocess.run(
            ["helm", "create", str(target_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print(f"[green]✓ Test chart created successfully at: {target_path}[/green]")
            console.print(f"[blue]You can now analyze it with: helm-previewer parse {target_path}[/blue]")
        else:
            console.print(f"[red]Error creating chart with helm: {result.stderr}[/red]")
            console.print("[yellow]Creating basic chart manually...[/yellow]")
            _create_basic_chart(target_path, name)
            
    except FileNotFoundError:
        console.print("[yellow]Helm command not found. Creating basic chart manually...[/yellow]")
        _create_basic_chart(target_path, name)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_charts(
    path: Optional[str] = typer.Option(None, "--path", help="Path to search for charts")
):
    """List available Helm charts in the specified path"""
    
    search_paths = []
    
    if path:
        search_paths.append(Path(path))
    else:
        # Default search locations
        search_paths.extend([
            Path.cwd(),
            Path.home() / "charts",
            Path("/usr/local/charts"),
            Path("/opt/charts")
        ])
    
    table = Table(title="Available Helm Charts")
    table.add_column("Chart Name", style="cyan")
    table.add_column("Path", style="blue")
    table.add_column("Version", style="green")
    
    charts_found = 0
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
            
        for item in search_path.iterdir():
            if item.is_dir() and (item / "Chart.yaml").exists():
                try:
                    import yaml
                    with open(item / "Chart.yaml", 'r') as f:
                        chart_info = yaml.safe_load(f)
                    
                    version = chart_info.get('version', 'unknown')
                    
                except Exception:
                    version = 'unknown'
                
                table.add_row(item.name, str(item.absolute()), version)
                charts_found += 1
    
    if charts_found == 0:
        console.print("[yellow]No Helm charts found in the specified locations[/yellow]")
    else:
        console.print(table)


def _display_chart_summary(chart_data, verbose: bool = False):
    """Display chart summary information"""
    
    # Chart metadata
    console.print(f"\n[bold blue]Chart: {chart_data.name}[/bold blue]")
    console.print(f"[blue]Version: {chart_data.metadata.version}[/blue]")
    if chart_data.metadata.description:
        console.print(f"[blue]Description: {chart_data.metadata.description}[/blue]")
    
    # Summary statistics
    summary = chart_data.summary
    
    table = Table(title="Chart Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Resources", str(summary.get('total_resources', 0)))
    table.add_row("Resource Types", str(summary.get('resource_types', 0)))
    table.add_row("Dependencies", str(summary.get('dependencies_count', 0)))
    table.add_row("Has Ingress", "✓" if summary.get('has_ingress') else "✗")
    table.add_row("Has Services", "✓" if summary.get('has_services') else "✗")
    table.add_row("Has Deployments", "✓" if summary.get('has_deployments') else "✗")
    
    console.print(table)
    
    # Resource breakdown
    if verbose and summary.get('kind_counts'):
        resource_table = Table(title="Resource Breakdown")
        resource_table.add_column("Resource Type", style="cyan")
        resource_table.add_column("Count", style="green")
        
        for kind, count in summary['kind_counts'].items():
            resource_table.add_row(kind, str(count))
        
        console.print(resource_table)


def _create_basic_chart(target_path: Path, name: str):
    """Create a basic chart structure manually"""
    
    target_path.mkdir(parents=True, exist_ok=True)
    
    # Create Chart.yaml
    chart_yaml = f"""apiVersion: v2
name: {name}
description: A basic Helm chart for testing
type: application
version: 0.1.0
appVersion: "1.0.0"
"""
    
    with open(target_path / "Chart.yaml", 'w') as f:
        f.write(chart_yaml)
    
    # Create values.yaml
    values_yaml = """replicaCount: 1

image:
  repository: nginx
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false
"""
    
    with open(target_path / "values.yaml", 'w') as f:
        f.write(values_yaml)
    
    # Create templates directory
    templates_dir = target_path / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Create basic deployment template
    deployment_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "chart.fullname" . }}
  labels:
    app: {{ .Values.name | default .Chart.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Values.name | default .Chart.Name }}
  template:
    metadata:
      labels:
        app: {{ .Values.name | default .Chart.Name }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 80
              protocol: TCP
"""
    
    with open(templates_dir / "deployment.yaml", 'w') as f:
        f.write(deployment_yaml)
    
    # Create basic service template
    service_yaml = """apiVersion: v1
kind: Service
metadata:
  name: {{ include "chart.fullname" . }}
  labels:
    app: {{ .Values.name | default .Chart.Name }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    app: {{ .Values.name | default .Chart.Name }}
"""
    
    with open(templates_dir / "service.yaml", 'w') as f:
        f.write(service_yaml)
    
    console.print(f"[green]✓ Basic chart created successfully at: {target_path}[/green]")


if __name__ == "__main__":
    app()
