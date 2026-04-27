import os
import csv
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse

# 1. Configuración inicial y rutas de archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METRICS_FILE = "metrics.csv"

app = FastAPI(title="RAGNAVOD Server")

# 2. Montaje de archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 3. Modelos de datos (Pydantic)
class VideoMetrics(BaseModel):
    video_name: str
    protocol: str
    load_time_ms: float
    avg_fragment_time: float
    buffering_events: int

# 4. Rutas de Interfaz (Frontend)
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "online", "protocol": "HTTP/3 candidate"}

# 5. Rutas de API y Métricas
@app.post("/api/log_metrics")
async def log_metrics(data: VideoMetrics):
    file_exists = os.path.isfile(METRICS_FILE)
    
    with open(METRICS_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        # Escribir cabecera si el archivo es nuevo
        if not file_exists:
            writer.writerow(["Timestamp", "Video", "Protocolo", "Startup_ms", "Avg_Frag_ms", "Stalls"])
        
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.video_name,
            data.protocol,
            data.load_time_ms,
            data.avg_fragment_time,
            data.buffering_events
        ])
    return {"status": "recorded"}

@app.get("/api/download_metrics")
async def download_metrics():
    # Retorna el archivo CSV generado
    return FileResponse(METRICS_FILE, filename="ragnavod_metrics.csv")