# Helm Chart Previewer

A CLI tool for visualizing Helm chart structure and dependencies with interactive HTML output.

## Features

- **CLI Interface**: Simple command-line tool with rich terminal output
- **Interactive Visualizations**: Beautiful network diagrams showing resource relationships
- **Comprehensive Analysis**: Detailed chart analysis with resource statistics and security assessment
- **Architecture Scoring**: Automatic evaluation of Kubernetes architecture completeness
- **HTML Reports**: Generate interactive HTML visualizations
- **Key Component Detection**: Special focus on ServiceAccount, Deployment, Service, and Ingress resources

## Quick Start

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

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

#### Basic Usage

```bash
# Analyze a Helm chart directory and generate HTML visualization
helm-previewer parse ./my-chart

# Specify output filename
helm-previewer parse ./my-chart --output my-chart-report.html

# Enable verbose output for detailed information
helm-previewer parse ./my-chart --verbose
```

#### Examples

```bash
# Analyze a chart in the current directory
helm-previewer parse .

# Analyze a chart with custom output name
helm-previewer parse ./nginx-chart --output nginx-analysis.html

# Get detailed breakdown of resources and relationships
helm-previewer parse ./my-microservice --verbose
```

## What You Get

The tool generates an interactive HTML visualization that includes:

### Architecture Analysis
- **Architecture Completeness Score**: 0-100% based on key components presence
- **Architecture Grading**: A+ (Complete) to D (Incomplete)
- **Key Components Status**: Visual indicators for ServiceAccount, Deployment, Service, Ingress

### Security Assessment
- **Security Score**: Comprehensive RBAC, ServiceAccount, and Secrets analysis
- **Recommendations**: Specific suggestions for improving security posture
- **Best Practices**: Guidance on Kubernetes security patterns

### Resource Analytics
- **Interactive Network Diagram**: Visual representation of resource relationships
- **Resource Categorization**: Organized by Workloads, Networking, Storage, Configuration, Security
- **Relationship Mapping**: Advanced detection of dependencies and interactions

### Interactive Features
- **Strategic Layout**: Key components positioned prominently
- **Color-coded Categories**: Different resource types use distinct colors and sizes
- **Hover Tooltips**: Detailed information on mouse hover
- **Responsive Design**: Works on desktop and mobile devices

## Architecture Components Detected

The tool specifically focuses on these key Kubernetes architecture components:

### Core Components
- **ServiceAccount**: Pod identity and authentication
- **Deployment**: Application workload management
- **Service**: Network abstraction and load balancing
- **Ingress**: External access and routing

### Supporting Resources
- **ConfigMap/Secret**: Configuration and sensitive data management
- **PersistentVolumeClaim**: Storage persistence
- **Role/RoleBinding**: RBAC permissions
- **HorizontalPodAutoscaler**: Auto-scaling configuration

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
│   ├── cli.py                    # Click-based CLI
│   ├── chart_parser.py           # Helm chart parsing logic
│   └── visualizer.py             # Visualization generation
├── tests/                        # Test files
├── pyproject.toml               # Project configuration
├── README.md
└── LICENSE
```

## Chart Support

The tool supports analyzing:

- **Local Helm Charts**: Any directory with a `Chart.yaml` file
- **Chart Archives**: After extraction to a directory
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

The tool works out-of-the-box with no configuration required. Simply point it at a Helm chart directory and it will:

1. Parse the Chart.yaml and values.yaml files
2. Analyze all template files in the templates/ directory
3. Detect relationships between resources
4. Generate a comprehensive HTML visualization

## Example Output

When you run `helm-previewer parse ./my-chart`, you'll see:

```
Chart: my-microservice
Version: 1.0.0
Description: A microservice application

┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric              ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Resources     │ 8     │
│ Resource Types      │ 6     │
│ Dependencies        │ 2     │
│ ServiceAccounts     │ 1     │
│ Deployments         │ 1     │
│ Services            │ 1     │
│ Ingresses           │ 1     │
│ Architecture Score  │ 100/100 │
│ Architecture Grade  │ A+ (Complete) │
│ Security Score      │ 80/100 │
└─────────────────────┴───────┘

HTML visualization saved to: my-microservice-visualization.html
```

The generated HTML file will contain an interactive dashboard with network diagrams, security analysis, and detailed resource information.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests and linting: `uv run pytest && uv run black . && uv run flake8`
5. Commit your changes: `git commit -am 'Add some feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for the CLI interface
- Visualizations powered by [Plotly](https://plotly.com/python/)
- Rich terminal output with [Rich](https://rich.readthedocs.io/)
- Charts parsed with [PyYAML](https://pyyaml.org/)
- Network analysis with [NetworkX](https://networkx.org/)
