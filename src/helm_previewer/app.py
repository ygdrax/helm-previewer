"""
FastAPI Web Application for Helm Chart Visualization
"""

import os
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Optional, List
import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .chart_parser import HelmChartParser, ChartData
from .visualizer import ChartVisualizer


# Pydantic models for API
class ChartParseRequest(BaseModel):
    chart_path: str


class ChartParseResponse(BaseModel):
    success: bool
    data: Optional[ChartData] = None
    error: Optional[str] = None


class NetworkDataResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


# Create FastAPI app
app = FastAPI(
    title="Helm Chart Previewer",
    description="A FastAPI-based viewer for Helm charts with interactive visualization",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Initialize components
parser = HelmChartParser()
visualizer = ChartVisualizer()

# Setup directories
UPLOAD_DIR = Path(tempfile.gettempdir()) / "helm-previewer-uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Setup templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Add static files if directory exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/parse", response_model=ChartParseResponse)
async def parse_chart_path(request: ChartParseRequest):
    """Parse a chart from a local path"""
    try:
        chart_path = Path(request.chart_path)
        
        if not chart_path.exists():
            raise HTTPException(status_code=404, detail=f"Chart path does not exist: {chart_path}")
        
        if not chart_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Chart path must be a directory: {chart_path}")
        
        chart_data = await parser.parse_chart(str(chart_path))
        
        return ChartParseResponse(success=True, data=chart_data)
        
    except Exception as e:
        return ChartParseResponse(success=False, error=str(e))


@app.post("/api/upload", response_model=ChartParseResponse)
async def upload_chart(file: UploadFile = File(...)):
    """Upload and parse a chart archive"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Create temporary directory for this upload
        upload_id = f"upload_{file.filename}_{hash(file.filename)}"
        upload_path = UPLOAD_DIR / upload_id
        upload_path.mkdir(exist_ok=True)
        
        # Save uploaded file
        file_path = upload_path / file.filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Extract if it's a zip file
        chart_dir = upload_path
        if file.filename.endswith(('.zip', '.tar.gz', '.tgz')):
            extract_dir = upload_path / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            if file.filename.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                # Handle tar.gz files
                import tarfile
                with tarfile.open(file_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            
            # Find the chart directory
            chart_dirs = [d for d in extract_dir.iterdir() if d.is_dir() and (d / "Chart.yaml").exists()]
            if chart_dirs:
                chart_dir = chart_dirs[0]
            else:
                chart_dir = extract_dir
        
        # Parse the chart
        chart_data = await parser.parse_chart(str(chart_dir))
        
        # Clean up
        shutil.rmtree(upload_path, ignore_errors=True)
        
        return ChartParseResponse(success=True, data=chart_data)
        
    except Exception as e:
        # Clean up on error
        if 'upload_path' in locals():
            shutil.rmtree(upload_path, ignore_errors=True)
        
        return ChartParseResponse(success=False, error=str(e))


@app.post("/api/visualize/html")
async def generate_html_visualization(request: ChartParseRequest):
    """Generate HTML visualization for a chart"""
    try:
        chart_data = await parser.parse_chart(request.chart_path)
        html_content = await visualizer.generate_interactive_html(chart_data)
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/visualize/network", response_model=NetworkDataResponse)
async def generate_network_data(request: ChartParseRequest):
    """Generate network data for frontend visualization"""
    try:
        chart_data = await parser.parse_chart(request.chart_path)
        network_data = await visualizer.generate_network_data(chart_data)
        
        return NetworkDataResponse(success=True, data=network_data)
        
    except Exception as e:
        return NetworkDataResponse(success=False, error=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.2.0"}


@app.get("/api/charts")
async def list_local_charts():
    """List local chart directories in common locations"""
    chart_locations = [
        Path.cwd(),
        Path.home() / "charts",
        Path("/usr/local/charts"),
        Path("/opt/charts")
    ]
    
    charts = []
    
    for location in chart_locations:
        if location.exists():
            for item in location.iterdir():
                if item.is_dir() and (item / "Chart.yaml").exists():
                    charts.append({
                        "name": item.name,
                        "path": str(item.absolute()),
                        "location": str(location)
                    })
    
    return {"charts": charts}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    return templates.TemplateResponse(
        "error.html", 
        {"request": request, "error_code": 404, "error_message": "Page not found"}, 
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    return templates.TemplateResponse(
        "error.html", 
        {"request": request, "error_code": 500, "error_message": "Internal server error"}, 
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
