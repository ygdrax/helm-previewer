#!/usr/bin/env python3
"""
Helm Chart Previewer - Main CLI Application
"""

import os
import sys
import click
import yaml
from pathlib import Path
from chart_parser import HelmChartParser
from visualizer import ChartVisualizer
from web_app import WebApp


@click.command()
@click.argument('chart_path', required=False)
@click.option('--web', is_flag=True, help='Start web interface')
@click.option('--output', '-o', default='chart_preview.html', help='Output file for visualization')
@click.option('--format', '-f', type=click.Choice(['html', 'png', 'svg', 'pdf']), default='html', help='Output format')
@click.option('--port', '-p', default=8080, help='Port for web interface')
@click.option('--host', default='localhost', help='Host for web interface')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def main(chart_path, web, output, format, port, host, debug):
    """
    Helm Chart Previewer - Visualize Helm chart structure and dependencies
    
    CHART_PATH: Path to Helm chart directory or chart name from repository
    """
    
    if web:
        # Start web interface
        app = WebApp(debug=debug)
        click.echo(f"Starting web interface at http://{host}:{port}")
        app.run(host=host, port=port)
        return
    
    if not chart_path:
        click.echo("Error: Chart path is required when not using --web mode")
        click.echo("Use 'helm-previewer --help' for more information")
        sys.exit(1)
    
    try:
        # Parse the chart
        click.echo(f"Parsing Helm chart: {chart_path}")
        parser = HelmChartParser()
        chart_data = parser.parse_chart(chart_path)
        
        # Generate visualization
        click.echo(f"Generating visualization in {format} format...")
        visualizer = ChartVisualizer()
        
        if format == 'html':
            html_content = visualizer.generate_interactive_html(chart_data)
            with open(output, 'w') as f:
                f.write(html_content)
        else:
            visualizer.generate_static_visualization(chart_data, output, format)
        
        click.echo(f"Visualization saved to: {output}")
        
        # Print summary
        print_chart_summary(chart_data)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def print_chart_summary(chart_data):
    """Print a summary of the chart structure"""
    click.echo("\n=== Chart Summary ===")
    click.echo(f"Chart Name: {chart_data.get('name', 'Unknown')}")
    click.echo(f"Version: {chart_data.get('version', 'Unknown')}")
    click.echo(f"Description: {chart_data.get('description', 'No description')}")
    
    templates = chart_data.get('templates', [])
    click.echo(f"\nTemplates ({len(templates)}):")
    for template in templates:
        click.echo(f"  - {template['name']} ({template['kind']})")
    
    dependencies = chart_data.get('dependencies', [])
    if dependencies:
        click.echo(f"\nDependencies ({len(dependencies)}):")
        for dep in dependencies:
            click.echo(f"  - {dep['name']} ({dep['version']})")
    
    values = chart_data.get('values', {})
    if values:
        click.echo(f"\nConfigurable Values: {len(values)} top-level keys")


if __name__ == '__main__':
    main()
