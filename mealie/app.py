import re
import warnings

# pyrdfa3 is no longer being updated and has docstrings that emit syntax warnings
warnings.filterwarnings(
    "ignore", module=".*pyRdfa", category=SyntaxWarning, message=re.escape("invalid escape sequence '\\-'")
)

# ruff: noqa: E402
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.routing import APIRoute
from starlette.middleware.sessions import SessionMiddleware

from mealie.core.config import get_app_settings
from mealie.core.root_logger import get_logger
from mealie.core.settings.static import APP_VERSION
from mealie.middleware.locale_context import LocaleContextMiddleware
from mealie.routes import router, spa, utility_routes
from mealie.routes.handlers import register_debug_handler
from mealie.routes.media import media_router
from mealie.services.scheduler import SchedulerRegistry, SchedulerService, tasks

settings = get_app_settings()

description = """
Mealie is a web application for managing your recipes, meal plans, and shopping lists. This is the Restful
API interactive documentation that can be used to explore the API. If you're justing getting started with
the API and want to get started quickly, you can use the
[API Usage | Mealie Docs](https://docs.mealie.io/documentation/getting-started/api-usage/)
as a reference for how to get started.


If you have any questions or comments about mealie, please use the discord server to talk to the developers or other
community members. If you'd like to file an issue, please use the
[GitHub Issue Tracker | Mealie](https://github.com/mealie-recipes/mealie/issues/new/choose)


## Helpful Links
- [Home Page](https://mealie.io)
- [Documentation](https://docs.mealie.io)
- [Discord](https://discord.gg/QuStdQGSGK)
- [Demo](https://demo.mealie.io)
"""

logger = get_logger()


@asynccontextmanager
async def lifespan_fn(_: FastAPI) -> AsyncGenerator[None, None]:
    """
    lifespan_fn controls the startup and shutdown of the FastAPI Application.
    This function is called when the FastAPI application starts and stops.

    See FastAPI documentation for more information:
      - https://fastapi.tiangolo.com/advanced/events/
    """
    logger.info("start: database initialization")
    import mealie.db.init_db as init_db

    init_db.main()
    logger.info("end: database initialization")

    logger.info("start: AI addon database initialization")
    import mealie.ai_addon.db.models  # noqa: F401 — registers all addon models in SqlAlchemyBase.metadata
    from mealie.db.db_setup import session_context
    from mealie.db.models._model_base import SqlAlchemyBase
    from sqlalchemy import inspect as sa_inspect

    with session_context() as _session:
        engine = _session.get_bind()
        # create_all is idempotent: creates addon tables that don't exist yet,
        # skips tables that already exist. Handles fresh container startups without
        # requiring a manual alembic migration step.
        addon_tables_meta = [
            t for t in SqlAlchemyBase.metadata.sorted_tables
            if t.name.startswith("ai_addon_")
        ]
        SqlAlchemyBase.metadata.create_all(bind=engine, tables=addon_tables_meta, checkfirst=True)
        inspector = sa_inspect(engine)
        addon_tables = [t for t in inspector.get_table_names() if t.startswith("ai_addon_")]
        logger.info(f"AI addon tables initialized: {addon_tables}")
    logger.info("end: AI addon database initialization")

    await start_scheduler()

    logger.info("-----SYSTEM STARTUP-----")
    logger.info("------APP SETTINGS------")
    logger.info(
        settings.model_dump_json(
            indent=4,
            exclude={
                "SECRET",
                "SESSION_SECRET",
                "DB_URL",  # replace by DB_URL_PUBLIC for logs
                "DB_PROVIDER",
            },
        )
    )
    logger.info("------APP FEATURES------")
    logger.info("--------==SMTP==--------")
    logger.info(settings.SMTP_FEATURE)
    logger.info("--------==LDAP==--------")
    logger.info(settings.LDAP_FEATURE)
    logger.info("--------==OIDC==--------")
    logger.info(settings.OIDC_FEATURE)
    logger.info("-------==OPENAI==-------")
    logger.info(settings.OPENAI_FEATURE)
    logger.info("-----==AI ADDON==-----")
    logger.info("AI Meal Planner addon loaded")
    logger.info("------------------------")

    yield

    logger.info("-----SYSTEM SHUTDOWN----- \n")


app = FastAPI(
    title="Mealie",
    description=description,
    version=APP_VERSION,
    docs_url=settings.DOCS_URL,
    lifespan=lifespan_fn,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)
app.add_middleware(LocaleContextMiddleware)

if not settings.PRODUCTION:
    allowed_origins = ["http://localhost:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

register_debug_handler(app)


async def start_scheduler():
    SchedulerRegistry.register_daily(
        tasks.purge_expired_tokens,
        tasks.purge_group_registration,
        tasks.purge_password_reset_tokens,
        tasks.purge_group_data_exports,
        tasks.create_mealplan_timeline_events,
        tasks.delete_old_checked_list_items,
    )

    SchedulerRegistry.register_minutely(
        tasks.post_group_webhooks,
    )

    SchedulerRegistry.register_hourly(
        tasks.locked_user_reset,
    )

    SchedulerRegistry.print_jobs()

    await SchedulerService.start()


def api_routers():
    app.include_router(router)
    app.include_router(media_router)
    app.include_router(utility_routes.router)

    if settings.PRODUCTION and not settings.TESTING:
        spa.mount_spa(app)


api_routers()

# fix routes that would get their tags duplicated by use of @controller,
# leading to duplicate definitions in the openapi spec
for route in app.routes:
    if isinstance(route, APIRoute):
        route.tags = list(set(route.tags))


def main():
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True,
        reload_dirs=["mealie"],
        reload_delay=2,
        log_level="info",
        use_colors=True,
        log_config=None,
        workers=1,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
