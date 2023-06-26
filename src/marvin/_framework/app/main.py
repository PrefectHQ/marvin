from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount the templates directory
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root(request: Request):
    # Return the index.html file
    return templates.TemplateResponse("index.html", {"request": request})
