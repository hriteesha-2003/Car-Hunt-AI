from fastapi import FastAPI


def gather_routers(app: FastAPI, routers: list) -> FastAPI:
    [app.include_router(router) for router in routers]
    return app

