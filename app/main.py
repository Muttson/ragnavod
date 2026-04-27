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

# 3. Modelos de datos (Pydantic) actualizados
class VideoMetrics(BaseModel):
    video_name: str
    protocol: str
    ttff_ms: float                  # Time to First Frame (TTFF)
    fragment_load_time_ms: float    # Fragment Load Time (Throughput)
    rebuffering_events: int         # Re-buffering Events
    inter_arrival_jitter_ms: float  # Inter-arrival Jitter (Std Dev de tiempos de carga)
    jitter_ms: float                # Steady State Stability (Jitter)

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
            writer.writerow([
                "Timestamp", 
                "Video", 
                "Protocolo", 
                "TTFF_ms", 
                "Frag_Load_Time_ms", 
                "Rebuffering_Events", 
                "Inter_Arrival_Jitter_ms", 
                "Jitter_ms"
            ])
        
        # Escribir los datos recibidos
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.video_name,
            data.protocol,
            data.ttff_ms,
            data.fragment_load_time_ms,
            data.rebuffering_events,
            data.inter_arrival_jitter_ms,
            data.jitter_ms
        ])
    return {"status": "recorded"}

@app.get("/api/download_metrics")
async def download_metrics():
    # Retorna el archivo CSV generado
    return FileResponse(METRICS_FILE, filename="ragnavod_metrics.csv")