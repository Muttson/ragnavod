from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI(title="RAGNAVOD Server")

# Montar carpeta para videos (aquí vivirá el streaming más adelante)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configurar plantillas HTML
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "online", "protocol": "HTTP/3 candidate"}