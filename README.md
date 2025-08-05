# Helm Chart Previewer

A modern FastAPI-based viewer for Helm charts with interactive visualization capabilities.

## Features

- **FastAPI Backend**: Modern, fast, and async API built with FastAPI
- **Interactive Visualizations**: Beautiful network diagrams showing resource relationships
- **Multiple Input Methods**: Upload charts or analyze local directories
- **Rich Web Interface**: Bootstrap-based responsive UI with drag-and-drop support
- **Detailed Analytics**: Comprehensive chart analysis with resource statistics
- **Export Options**: Generate HTML reports and download JSON data
- **CLI Tool**: Command-line interface with rich terminal output
- **Modern Python**: Built with Python 3.9+ using modern async/await patterns

## Quick Start

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Helm CLI (optional, for enhanced chart parsing)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ygdrax/helm-previewer.git
   cd helm-previewer
   ```

2. **Install with uv:**
   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install the project and dependencies
   uv sync
   ```

3. **Install in development mode:**
   ```bash
   uv pip install -e .
   ```

### Usage

#### Web Interface

Start the web server:
```bash
# Using the CLI
helm-previewer serve

# Or directly with uvicorn
uv run uvicorn helm_previewer.app:app --host 0.0.0.0 --port 8080 --reload
```

Visit `http://localhost:8080` in your browser.

#### Command Line Interface

```bash
# Analyze a local chart
helm-previewer parse ./my-chart

# Generate HTML visualization
helm-previewer parse ./my-chart --output chart-report.html --format html

# Generate JSON data
helm-previewer parse ./my-chart --output chart-data.json --format json

# Create a test chart
helm-previewer create-test-chart my-test-chart

# List available local charts
helm-previewer list-charts

# Start web server with custom settings
helm-previewer serve --host 0.0.0.0 --port 3000 --reload
```

## API Documentation

When the server is running, visit:
- Swagger UI: `http://localhost:8080/api/docs`
- ReDoc: `http://localhost:8080/api/redoc`

### Key API Endpoints

- `POST /api/parse` - Parse a chart from local path
- `POST /api/upload` - Upload and parse a chart archive
- `POST /api/visualize/html` - Generate HTML visualization
- `POST /api/visualize/network` - Get network data for custom visualizations
- `GET /api/charts` - List available local charts
- `GET /api/health` - Health check

## Development

### Setting up Development Environment

```bash
# Clone and setup
git clone https://github.com/ygdrax/helm-previewer.git
cd helm-previewer

# Install with development dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=helm_previewer

# Run specific test file
uv run pytest tests/test_parser.py
```

### Code Formatting and Linting

```bash
# Format code
uv run black src/helm_previewer tests

# Sort imports
uv run isort src/helm_previewer tests

# Type checking
uv run mypy src/helm_previewer

# Lint code
uv run flake8 src/helm_previewer
```

### Project Structure

```
helm-previewer/
├── src/helm_previewer/           # Main package
│   ├── __init__.py
│   ├── app.py                    # FastAPI application
│   ├── cli.py                    # CLI using Typer
│   ├── chart_parser.py           # Helm chart parsing logic
│   ├── visualizer.py             # Visualization generation
│   └── templates/                # Jinja2 templates
│       ├── index.html
│       └── error.html
├── tests/                        # Test files
├── pyproject.toml               # Project configuration
├── README.md
└── LICENSE
```

## Chart Support

The tool supports analyzing:

- **Local Helm Charts**: Any directory with a `Chart.yaml` file
- **Chart Archives**: `.zip`, `.tar.gz`, `.tgz` files containing charts
- **Chart Repositories**: Charts from Helm repositories (via local path after `helm pull`)

### Supported Kubernetes Resources

- Deployments, StatefulSets, DaemonSets
- Services, Ingress
- ConfigMaps, Secrets
- Jobs, CronJobs
- PersistentVolumes, PersistentVolumeClaims
- ServiceAccounts, Roles, RoleBindings
- HorizontalPodAutoscalers
- NetworkPolicies

## Configuration

### Environment Variables

- `HELM_PREVIEWER_HOST`: Default host for web server (default: localhost)
- `HELM_PREVIEWER_PORT`: Default port for web server (default: 8080)
- `HELM_PREVIEWER_DEBUG`: Enable debug mode (default: false)

### Chart Parsing Options

The parser supports:
- Template rendering with Helm CLI (when available)
- Fallback YAML parsing for offline analysis
- Dependency resolution from Chart.yaml and charts/ directory
- Resource relationship analysis

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests and linting: `uv run pytest && uv run black . && uv run flake8`
5. Commit your changes: `git commit -am 'Add some feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## Migration from v0.1.x

This version represents a complete rewrite using modern tools:

### Key Changes

- **Framework**: Migrated from Flask to FastAPI
- **Package Management**: Now uses `uv` instead of pip/setuptools
- **Project Structure**: Modern `pyproject.toml` configuration
- **CLI**: New Typer-based CLI with rich terminal output
- **Async Support**: Full async/await support throughout
- **Type Hints**: Complete type annotations with Pydantic models
- **Modern Dependencies**: Updated to latest versions of all dependencies

### Breaking Changes

- CLI commands have changed (see usage section)
- API endpoints have new structure
- Configuration format updated
- Python 3.9+ required

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Visualizations powered by [Plotly](https://plotly.com/python/)
- CLI built with [Typer](https://typer.tiangolo.com/)
- Package management with [uv](https://github.com/astral-sh/uv)
- Charts parsed with [PyYAML](https://pyyaml.org/)
- Network analysis with [NetworkX](https://networkx.org/)
- `visualizer.py` - Chart visualization engine
- `web_app.py` - Web interface
- `templates/` - HTML templates for web interface
- `static/` - CSS/JS for web interface
