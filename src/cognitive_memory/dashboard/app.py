"""FastAPI application factory for cogmem dashboard."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import CogMemConfig
from .i18n import t

DASHBOARD_DIR = Path(__file__).parent
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"


def get_lang(request: Request) -> str:
    """Get language from cookie, default to 'en'."""
    return request.cookies.get("lang", "en")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app(config: CogMemConfig) -> FastAPI:
    app = FastAPI(title="cogmem dashboard", lifespan=lifespan)

    app.state.config = config
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.templates = templates

    # Register i18n globals — available in all templates without per-route injection
    templates.env.globals["t"] = t
    templates.env.globals["get_lang"] = get_lang

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Language switch route
    lang_router = APIRouter()

    @lang_router.get("/_lang/{lang}")
    async def switch_lang(request: Request, lang: str):
        lang = lang if lang in ("en", "ja") else "en"
        referer = request.headers.get("referer", "/")
        response = RedirectResponse(url=referer, status_code=302)
        response.set_cookie("lang", lang, max_age=365 * 24 * 3600)
        return response

    app.include_router(lang_router)

    from .routes.consolidation import router as consolidation_router
    from .routes.logs import router as logs_router
    from .routes.memory import router as memory_router
    from .routes.personality import router as personality_router
    from .routes.search import router as search_router
    from .routes.skills import router as skills_router
    from .routes.system import router as system_router

    app.include_router(memory_router)
    app.include_router(skills_router, prefix="/skills")
    app.include_router(logs_router, prefix="/logs")
    app.include_router(search_router, prefix="/search")
    app.include_router(personality_router, prefix="/personality")
    app.include_router(consolidation_router, prefix="/consolidation")
    app.include_router(system_router, prefix="/system")

    return app
