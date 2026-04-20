import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Obtener la ruta absoluta del directorio actual (donde está main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="RAGNAVOD Server")

# Usar rutas absolutas para montar static y templates
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "online", "protocol": "HTTP/3 candidate"}