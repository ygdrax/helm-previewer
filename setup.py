#!/usr/bin/env python3
"""
Setup script for Helm Chart Previewer
"""

import subprocess
import sys
import os
from pathlib import Path


def install_requirements():
    """Install required Python packages"""
    print("Installing required packages...")
    
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ All packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False


def create_test_chart():
    """Create a test Helm chart for demonstration"""
    print("Creating test Helm chart...")
    
    test_dir = Path("./test-chart")
    
    # Remove existing test chart
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
    
    try:
        # Try to use helm to create chart
        result = subprocess.run(['helm', 'create', 'test-chart'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Test chart created with Helm!")
            return True
        else:
            print("⚠️  Helm not found, creating manual test chart...")
            return create_manual_test_chart()
    except FileNotFoundError:
        print("⚠️  Helm not found, creating manual test chart...")
        return create_manual_test_chart()


def create_manual_test_chart():
    """Create a manual test chart when Helm is not available"""
    test_dir = Path("./test-chart")
    test_dir.mkdir(exist_ok=True)
    
    # Create Chart.yaml
    chart_yaml = """apiVersion: v2
name: test-chart
description: A test Helm chart for demonstration
type: application
version: 0.1.0
appVersion: "1.0"
"""
    (test_dir / "Chart.yaml").write_text(chart_yaml)
    
    # Create values.yaml
    values_yaml = """replicaCount: 1

image:
  repository: nginx
  pullPolicy: IfNotPresent
  tag: "1.21"

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false
  className: ""
  annotations: {}
  hosts:
    - host: chart-example.local
      paths:
        - path: /
          pathType: Prefix
  tls: []

resources: {}
nodeSelector: {}
tolerations: []
affinity: {}
"""
    (test_dir / "values.yaml").write_text(values_yaml)
    
    # Create templates directory
    templates_dir = test_dir / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Create deployment template
    deployment_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Chart.Name }}
  labels:
    app: {{ .Chart.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Chart.Name }}
  template:
    metadata:
      labels:
        app: {{ .Chart.Name }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 80
              protocol: TCP
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
"""
    (templates_dir / "deployment.yaml").write_text(deployment_yaml)
    
    # Create service template
    service_yaml = """apiVersion: v1
kind: Service
metadata:
  name: {{ .Chart.Name }}-service
  labels:
    app: {{ .Chart.Name }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    app: {{ .Chart.Name }}
"""
    (templates_dir / "service.yaml").write_text(service_yaml)
    
    # Create configmap template
    configmap_yaml = """apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Chart.Name }}-config
  labels:
    app: {{ .Chart.Name }}
data:
  app.properties: |
    name={{ .Chart.Name }}
    version={{ .Chart.Version }}
    environment=production
"""
    (templates_dir / "configmap.yaml").write_text(configmap_yaml)
    
    print("✅ Manual test chart created!")
    return True


def run_demo():
    """Run a demo of the chart previewer"""
    print("\n🚀 Running demo...")
    print("Demo options:")
    print("1. CLI mode: python helm_previewer.py ./test-chart")
    print("2. Web mode: python helm_previewer.py --web")
    print("3. Generate HTML: python helm_previewer.py ./test-chart -o demo.html")
    
    choice = input("\nEnter choice (1/2/3) or press Enter to skip: ").strip()
    
    if choice == "1":
        os.system("python helm_previewer.py ./test-chart")
    elif choice == "2":
        print("Starting web interface at http://localhost:8080")
        print("Press Ctrl+C to stop")
        os.system("python helm_previewer.py --web")
    elif choice == "3":
        os.system("python helm_previewer.py ./test-chart -o demo.html")
        print("✅ Demo HTML created: demo.html")


def main():
    """Main setup function"""
    print("🔧 Helm Chart Previewer Setup")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version}")
    
    # Install requirements
    if not install_requirements():
        print("❌ Setup failed at package installation")
        sys.exit(1)
    
    # Create test chart
    if not create_test_chart():
        print("❌ Setup failed at test chart creation")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Analyze the test chart: python helm_previewer.py ./test-chart")
    print("2. Start web interface: python helm_previewer.py --web")
    print("3. Create your own chart: helm create my-chart")
    
    # Offer to run demo
    run_demo()


if __name__ == "__main__":
    main()
