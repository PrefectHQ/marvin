from importlib.metadata import version

import sqlalchemy as sa
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

import marvin

logger = marvin.get_logger("app")

routers = (
    marvin.api.bots.router,
    marvin.api.topics.router,
    marvin.api.threads.router,
)


app = FastAPI(title="Marvin", version=version("marvin"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for router in routers:
    app.include_router(router)


@app.exception_handler(sa.exc.IntegrityError)
async def integrity_error_handler(request: Request, exc: sa.exc.IntegrityError):
    logger.warning(exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": "Integrity error"}
    )


@app.get("/", response_class=RedirectResponse, tags=["Admin"])
def hello():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Admin"])
def health():
    return True
