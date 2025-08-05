"""
CLI Application using Click for Helm Chart Previewer
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .chart_parser import HelmChartParser
from .visualizer import ChartVisualizer

console = Console()


@click.group()
@click.version_option(version="0.3.0")
def cli():
    """Helm Chart Previewer - Visualize Helm chart structure and dependencies"""
    pass


@cli.command()
@click.argument(
    "chart_path", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option(
    "--output", "-o", type=click.Path(), help="Output file for HTML visualization"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def parse(chart_path: str, output: str | None, verbose: bool):
    """Parse a Helm chart directory and generate HTML visualization"""

    async def _parse_chart():
        chart_path_obj = Path(chart_path)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Parse chart
            task = progress.add_task("Parsing Helm chart...", total=None)
            parser = HelmChartParser()
            chart_data = await parser.parse_chart(str(chart_path_obj))
            progress.remove_task(task)

            # Display summary
            _display_chart_summary(chart_data, verbose)

            # Generate HTML output
            output_file = output
            if not output_file:
                # Default output filename
                output_file = f"{chart_data.name}-visualization.html"

            task = progress.add_task("Generating HTML visualization...", total=None)

            visualizer = ChartVisualizer()
            html_content = await visualizer.generate_interactive_html(chart_data)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            progress.remove_task(task)
            console.print(
                f"[green]✓ HTML visualization saved to: {output_file}[/green]"
            )

    try:
        asyncio.run(_parse_chart())
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


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

    table.add_row("Total Resources", str(summary.get("total_resources", 0)))
    table.add_row("Resource Types", str(summary.get("resource_types", 0)))
    table.add_row("Dependencies", str(summary.get("dependencies_count", 0)))

    # Enhanced summary with key components
    if "key_components" in summary:
        key_components = summary["key_components"]
        table.add_row("ServiceAccounts", str(key_components.get("service_accounts", 0)))
        table.add_row("Deployments", str(key_components.get("deployments", 0)))
        table.add_row("Services", str(key_components.get("services", 0)))
        table.add_row("Ingresses", str(key_components.get("ingresses", 0)))

        table.add_row(
            "Architecture Score", f"{summary.get('architecture_score', 0)}/100"
        )
        table.add_row(
            "Architecture Grade", summary.get("architecture_grade", "Unknown")
        )
        table.add_row("Security Score", f"{summary.get('security_score', 0)}/100")
    else:
        # Fallback for older format
        table.add_row("Has Ingress", "✓" if summary.get("has_ingress") else "✗")
        table.add_row("Has Services", "✓" if summary.get("has_services") else "✗")
        table.add_row("Has Deployments", "✓" if summary.get("has_deployments") else "✗")

    console.print(table)

    # Resource breakdown
    if verbose and summary.get("kind_counts"):
        resource_table = Table(title="Resource Breakdown")
        resource_table.add_column("Resource Type", style="cyan")
        resource_table.add_column("Count", style="green")

        for kind, count in summary["kind_counts"].items():
            resource_table.add_row(kind, str(count))

        console.print(resource_table)

    # Relationships
    if verbose and hasattr(chart_data, "relationships") and chart_data.relationships:
        relationships_table = Table(title="Resource Relationships")
        relationships_table.add_column("Source", style="cyan")
        relationships_table.add_column("Relationship", style="yellow")
        relationships_table.add_column("Target", style="green")

        for rel in chart_data.relationships:
            source = f"{rel['source']['kind']}:{rel['source']['name']}"
            target = f"{rel['target']['kind']}:{rel['target']['name']}"
            rel_type = rel["type"]
            relationships_table.add_row(source, rel_type, target)

        console.print(relationships_table)


if __name__ == "__main__":
    cli()
