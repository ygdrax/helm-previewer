"""
Basic tests for Helm Chart Previewer
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from helm_previewer.chart_parser import HelmChartParser


@pytest.mark.asyncio
async def test_parser_creation():
    """Test that we can create a parser instance"""
    parser = HelmChartParser()
    assert parser is not None
    assert hasattr(parser, "parse_chart")


@pytest.mark.asyncio
async def test_parse_simple_chart():
    """Test parsing a simple chart"""
    with tempfile.TemporaryDirectory() as tmpdir:
        chart_dir = Path(tmpdir) / "test-chart"
        chart_dir.mkdir()
        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()

        # Create Chart.yaml
        chart_yaml = {
            "apiVersion": "v2",
            "name": "test-chart",
            "version": "1.0.0",
            "description": "A test chart",
        }
        with open(chart_dir / "Chart.yaml", "w") as f:
            yaml.dump(chart_yaml, f)

        # Create a simple deployment template
        deployment_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test-app
  template:
    metadata:
      labels:
        app: test-app
    spec:
      containers:
      - name: app
        image: nginx:latest
"""
        with open(templates_dir / "deployment.yaml", "w") as f:
            f.write(deployment_yaml)

        # Parse the chart
        parser = HelmChartParser()
        chart_data = await parser.parse_chart(str(chart_dir))

        # Verify basic structure
        assert chart_data.name == "test-chart"
        assert chart_data.metadata.name == "test-chart"
        assert chart_data.metadata.version == "1.0.0"
        assert len(chart_data.resources) >= 1

        # Check if we found the deployment
        deployment_found = any(r.kind == "Deployment" for r in chart_data.resources)
        assert deployment_found, "Should find at least one Deployment"


def test_cli_import():
    """Test that we can import the CLI module"""
    from helm_previewer.cli import cli

    assert cli is not None


def test_visualizer_import():
    """Test that we can import the visualizer module"""
    from helm_previewer.visualizer import ChartVisualizer

    assert ChartVisualizer is not None
