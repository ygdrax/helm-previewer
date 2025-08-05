"""
Tests for Helm Chart Parser
"""

import pytest
import tempfile
import os
from pathlib import Path

from helm_previewer.chart_parser import HelmChartParser, ChartData, ChartMetadata


@pytest.fixture
def sample_chart_dir():
    """Create a temporary chart directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        chart_dir = Path(temp_dir) / "test-chart"
        chart_dir.mkdir()
        
        # Create Chart.yaml
        chart_yaml = """apiVersion: v2
name: test-chart
description: A test Helm chart
type: application
version: 0.1.0
appVersion: "1.0.0"
"""
        with open(chart_dir / "Chart.yaml", "w") as f:
            f.write(chart_yaml)
        
        # Create values.yaml
        values_yaml = """replicaCount: 1
image:
  repository: nginx
  tag: latest
"""
        with open(chart_dir / "values.yaml", "w") as f:
            f.write(values_yaml)
        
        # Create templates directory
        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()
        
        # Create a simple deployment template
        deployment_yaml = """apiVersion: apps/v1
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
      - name: nginx
        image: nginx:latest
"""
        with open(templates_dir / "deployment.yaml", "w") as f:
            f.write(deployment_yaml)
        
        yield chart_dir


@pytest.mark.asyncio
async def test_parse_chart_basic(sample_chart_dir):
    """Test basic chart parsing functionality"""
    parser = HelmChartParser()
    
    chart_data = await parser.parse_chart(str(sample_chart_dir))
    
    assert isinstance(chart_data, ChartData)
    assert chart_data.name == "test-chart"
    assert chart_data.metadata.version == "0.1.0"
    assert chart_data.metadata.name == "test-chart"


@pytest.mark.asyncio
async def test_parse_chart_metadata(sample_chart_dir):
    """Test chart metadata parsing"""
    parser = HelmChartParser()
    
    chart_data = await parser.parse_chart(str(sample_chart_dir))
    
    metadata = chart_data.metadata
    assert metadata.name == "test-chart"
    assert metadata.version == "0.1.0"
    assert metadata.description == "A test Helm chart"
    assert metadata.type_ == "application"
    assert metadata.api_version == "v2"


@pytest.mark.asyncio
async def test_parse_chart_values(sample_chart_dir):
    """Test values parsing"""
    parser = HelmChartParser()
    
    chart_data = await parser.parse_chart(str(sample_chart_dir))
    
    values = chart_data.values
    assert values["replicaCount"] == 1
    assert values["image"]["repository"] == "nginx"
    assert values["image"]["tag"] == "latest"


@pytest.mark.asyncio
async def test_parse_chart_nonexistent():
    """Test parsing non-existent chart"""
    parser = HelmChartParser()
    
    with pytest.raises(FileNotFoundError):
        await parser.parse_chart("/nonexistent/path")


@pytest.mark.asyncio
async def test_parse_chart_not_directory():
    """Test parsing a file instead of directory"""
    parser = HelmChartParser()
    
    with tempfile.NamedTemporaryFile() as temp_file:
        with pytest.raises(ValueError, match="Chart path must be a directory"):
            await parser.parse_chart(temp_file.name)


def test_supported_kinds():
    """Test that parser has expected supported kinds"""
    parser = HelmChartParser()
    
    expected_kinds = {
        'Deployment', 'Service', 'ConfigMap', 'Secret', 'Ingress',
        'StatefulSet', 'DaemonSet', 'Job', 'CronJob'
    }
    
    assert expected_kinds.issubset(parser.supported_kinds)
