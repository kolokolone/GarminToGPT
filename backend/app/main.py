from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api import routes_auth, routes_logs, routes_mcp, routes_status, routes_tests, routes_tunnel
from app.core.config import get_settings
from app.core.paths import project_root


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app.name, version=settings.app.version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://127.0.0.1:{settings.server.frontend_port}",
            f"http://localhost:{settings.server.frontend_port}",
            f"http://127.0.0.1:{settings.server.backend_port}",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(routes_status.router)
    app.include_router(routes_auth.router)
    app.include_router(routes_mcp.router)
    app.include_router(routes_tunnel.router)
    app.include_router(routes_logs.router)
    app.include_router(routes_tests.router)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    static_dir = project_root() / "frontend" / "out"
    if static_dir.exists():
        register_frontend_routes(app, static_dir)
        app.mount("/", StaticFiles(directory=Path(static_dir), html=True), name="frontend")
    return app


def register_frontend_routes(app: FastAPI, static_dir: Path) -> None:
    def page(filename: str) -> FileResponse:
        path = static_dir / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Frontend build not found")
        return FileResponse(path)

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    def home() -> FileResponse:
        return page("index.html")

    @app.api_route("/connexion", methods=["GET", "HEAD"], include_in_schema=False)
    def connexion() -> FileResponse:
        return page("connexion.html")

    @app.api_route("/tests", methods=["GET", "HEAD"], include_in_schema=False)
    def tests() -> FileResponse:
        return page("tests.html")

    @app.get("/connexion/__next.connexion.__PAGE__.txt", include_in_schema=False)
    def connexion_page_rsc() -> FileResponse:
        return page("connexion.txt")

    @app.get("/tests/__next.tests.__PAGE__.txt", include_in_schema=False)
    def tests_page_rsc() -> FileResponse:
        return page("tests.txt")


app = create_app()
