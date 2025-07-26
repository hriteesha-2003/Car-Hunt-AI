from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import status
import logging
from app.database.connections import lifespan
from app.includes import get_all_routers
from tools.routers import gather_routers
# from fastapi.staticfiles import StaticFiles
from app.socketio.socket_server import sio_app


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("🚀 Starting FastAPI application")

app = FastAPI(
    title="MotorFinder API",
    description="API for Felp Registration",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)
routers = get_all_routers()
app = gather_routers(app, routers)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/", sio_app)  

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An unexpected error occurred."},
    )


@app.get("/")
async def Index(req: Request):
    return {"message": "Welcome to MotorFinder API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
