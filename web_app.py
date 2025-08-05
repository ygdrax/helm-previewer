"""
Web Application - Flask-based web interface for Helm chart visualization
"""

import os
import json
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import zipfile
from pathlib import Path
from chart_parser import HelmChartParser
from visualizer import ChartVisualizer


class WebApp:
    """Flask web application for Helm chart visualization"""
    
    def __init__(self, debug=False):
        self.app = Flask(__name__)
        self.app.secret_key = 'helm-previewer-secret-key'
        self.debug = debug
        self.parser = HelmChartParser()
        self.visualizer = ChartVisualizer()
        
        # Setup routes
        self._setup_routes()
        
        # Create upload directory
        self.upload_dir = Path(tempfile.gettempdir()) / 'helm-previewer-uploads'
        self.upload_dir.mkdir(exist_ok=True)
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main page"""
            return self._render_index()
        
        @self.app.route('/api/parse', methods=['POST'])
        def parse_chart():
            """API endpoint to parse a chart"""
            try:
                if 'chart_path' in request.json:
                    # Parse from local path
                    chart_path = request.json['chart_path']
                    chart_data = self.parser.parse_chart(chart_path)
                elif 'file' in request.files:
                    # Parse from uploaded file
                    file = request.files['file']
                    if file.filename == '':
                        return jsonify({'error': 'No file selected'}), 400
                    
                    # Save uploaded file
                    filename = secure_filename(file.filename)
                    filepath = self.upload_dir / filename
                    file.save(filepath)
                    
                    # Extract if it's a zip file
                    if filename.endswith('.zip'):
                        extract_dir = self.upload_dir / filename[:-4]
                        with zipfile.ZipFile(filepath, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                        chart_path = extract_dir
                    else:
                        chart_path = filepath.parent
                    
                    chart_data = self.parser.parse_chart(chart_path)
                else:
                    return jsonify({'error': 'No chart path or file provided'}), 400
                
                return jsonify(chart_data)
            
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/visualize', methods=['POST'])
        def visualize_chart():
            """API endpoint to generate visualization"""
            try:
                chart_data = request.json
                html_content = self.visualizer.generate_interactive_html(chart_data)
                return html_content
            
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/examples')
        def get_examples():
            """Get example charts"""
            examples = [
                {
                    'name': 'nginx',
                    'description': 'Simple nginx deployment',
                    'command': 'helm create nginx'
                },
                {
                    'name': 'wordpress',
                    'description': 'WordPress with MySQL',
                    'command': 'helm repo add bitnami https://charts.bitnami.com/bitnami && helm pull bitnami/wordpress'
                }
            ]
            return jsonify(examples)
    
    def _render_index(self):
        """Render the main index page"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Helm Chart Previewer</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            padding: 40px;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .header h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .header p {
            color: #666;
            font-size: 1.2em;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        .tab {
            padding: 12px 24px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.3s;
        }
        .tab.active {
            border-bottom-color: #667eea;
            color: #667eea;
            font-weight: bold;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .examples {
            margin-top: 30px;
        }
        .example-item {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #667eea;
            border-radius: 5px;
        }
        .loading {
            text-align: center;
            padding: 20px;
            display: none;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            display: none;
        }
        .result {
            margin-top: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Helm Chart Previewer</h1>
            <p>Visualize and analyze your Helm charts structure and relationships</p>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="switchTab('path')">Local Path</div>
            <div class="tab" onclick="switchTab('upload')">Upload Chart</div>
            <div class="tab" onclick="switchTab('examples')">Examples</div>
        </div>
        
        <div id="path-tab" class="tab-content active">
            <form id="path-form">
                <div class="form-group">
                    <label for="chart-path">Chart Directory Path:</label>
                    <input type="text" id="chart-path" name="chart_path" 
                           placeholder="/path/to/your/helm/chart" required>
                </div>
                <button type="submit" class="btn">Analyze Chart</button>
            </form>
        </div>
        
        <div id="upload-tab" class="tab-content">
            <form id="upload-form">
                <div class="form-group">
                    <label for="chart-file">Upload Chart Archive (.zip):</label>
                    <input type="file" id="chart-file" name="file" accept=".zip" required>
                </div>
                <button type="submit" class="btn">Upload & Analyze</button>
            </form>
        </div>
        
        <div id="examples-tab" class="tab-content">
            <div class="examples">
                <div class="example-item">
                    <h4>Create a test chart</h4>
                    <p>Run: <code>helm create test</code></p>
                    <p>Then analyze: <code>./test</code></p>
                </div>
                <div class="example-item">
                    <h4>Download Bitnami WordPress</h4>
                    <p>Run: <code>helm repo add bitnami https://charts.bitnami.com/bitnami</code></p>
                    <p>Run: <code>helm pull bitnami/wordpress --untar</code></p>
                    <p>Then analyze: <code>./wordpress</code></p>
                </div>
            </div>
        </div>
        
        <div class="loading">
            <p>🔄 Analyzing chart...</p>
        </div>
        
        <div class="error" id="error-message"></div>
        
        <div class="result" id="result">
            <h3>Chart Analysis Complete!</h3>
            <p>The visualization will open in a new window.</p>
        </div>
    </div>

    <script>
        function switchTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
        }
        
        function showLoading() {
            document.querySelector('.loading').style.display = 'block';
            document.querySelector('.error').style.display = 'none';
            document.querySelector('.result').style.display = 'none';
        }
        
        function hideLoading() {
            document.querySelector('.loading').style.display = 'none';
        }
        
        function showError(message) {
            const errorEl = document.getElementById('error-message');
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
        
        function showResult() {
            document.querySelector('.result').style.display = 'block';
        }
        
        // Handle path form
        document.getElementById('path-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            showLoading();
            
            const chartPath = document.getElementById('chart-path').value;
            
            try {
                // Parse chart
                const parseResponse = await fetch('/api/parse', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({chart_path: chartPath})
                });
                
                if (!parseResponse.ok) {
                    throw new Error('Failed to parse chart');
                }
                
                const chartData = await parseResponse.json();
                
                // Generate visualization
                const vizResponse = await fetch('/api/visualize', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(chartData)
                });
                
                if (!vizResponse.ok) {
                    throw new Error('Failed to generate visualization');
                }
                
                const htmlContent = await vizResponse.text();
                
                // Open in new window
                const newWindow = window.open();
                newWindow.document.write(htmlContent);
                newWindow.document.close();
                
                hideLoading();
                showResult();
                
            } catch (error) {
                hideLoading();
                showError('Error: ' + error.message);
            }
        });
        
        // Handle upload form
        document.getElementById('upload-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            showLoading();
            
            const formData = new FormData();
            const fileInput = document.getElementById('chart-file');
            formData.append('file', fileInput.files[0]);
            
            try {
                // Upload and parse chart
                const parseResponse = await fetch('/api/parse', {
                    method: 'POST',
                    body: formData
                });
                
                if (!parseResponse.ok) {
                    throw new Error('Failed to parse uploaded chart');
                }
                
                const chartData = await parseResponse.json();
                
                // Generate visualization
                const vizResponse = await fetch('/api/visualize', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(chartData)
                });
                
                if (!vizResponse.ok) {
                    throw new Error('Failed to generate visualization');
                }
                
                const htmlContent = await vizResponse.text();
                
                // Open in new window
                const newWindow = window.open();
                newWindow.document.write(htmlContent);
                newWindow.document.close();
                
                hideLoading();
                showResult();
                
            } catch (error) {
                hideLoading();
                showError('Error: ' + error.message);
            }
        });
    </script>
</body>
</html>
        """
        return html_content
    
    def run(self, host='localhost', port=8080):
        """Run the Flask application"""
        self.app.run(host=host, port=port, debug=self.debug)
