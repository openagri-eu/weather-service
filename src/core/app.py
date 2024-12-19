from functools import partial
import logging
import fastapi
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document

from src.core import config
from src import utils
from src import gatekeeper_utils as gk_utils
from src.core.dao import Dao
from src.api.api import api_router
from src.api.auth import auth_router
from src.external_services.openweathermap import OpenWeatherMap


logger = logging.getLogger(__name__)

class Application(fastapi.FastAPI):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dao = self.setup_dao()
        self.weather_app = self.setup_weather_app()
        self.setup_routes()
        self.setup_openapi()
        self.setup_middlewares()


    def setup_dao(self):

        async def db_up(app: Application):
            await app.dao.db.admin.command('ping')
            logger.debug("You successfully connected to MongoDB!")
            # Init beanie with the Product document class
            await init_beanie(
                database=app.dao.db.get_database(config.DATABASE_NAME),
                document_models=utils.load_classes('**/models/**.py', (Document,))
            )

        async def db_down(app: Application):
            app.dao.db.close()
            logger.debug("Database closed!")

        self.add_event_handler(event_type="startup", func=partial(db_up, app=self))
        self.add_event_handler(event_type='shutdown', func=partial(db_down, app=self))
        return Dao(AsyncIOMotorClient(config.DATABASE_URI))

    def setup_routes(self):

        async def add_router(app: Application):
            logger.debug("Setup routes")
            app.include_router(api_router)
            app.include_router(auth_router)
            logger.debug("Routes added!")

        async def register_routes(app: Application):
            logger.debug("Registering routes to Gatekeeper")

            token, refresh = await gk_utils.gk_login()
            logging.debug(f"Obtained JWT token from gatekeeper: {token}")

            service_directory = await gk_utils.gk_service_directory(token)
            logging.debug(f"Fetched service directory: {service_directory}")

            app_routes = utils.list_routes_from_routers([api_router])
            logging.debug(f"App routes: {app_routes}")

            existing_endpoints = {entry["endpoint"]: entry for entry in service_directory}
            for route in app_routes:
                relative_path = route["path"].lstrip("/")
                if relative_path not in existing_endpoints:
                    service_data = {
                        "base_url": f"{config.WEATHER_SRV_HOSTNAME}:{config.WEATHER_SRV_PORT}",
                        "service_name": "weather_data",
                        "endpoint": relative_path,
                        "methods": route["methods"],
                        # "params": "lat{float}&lon{float}",
                    }
                    response = await gk_utils.gk_service_register(token, service_data)
                    logging.info(f"Registered new service: {response}")

            await gk_utils.gk_logout(refresh)


        self.add_event_handler(event_type="startup", func=partial(add_router, app=self))
        if config.GATEKEEPER_URL:
            self.add_event_handler(event_type="startup", func=partial(register_routes, app=self))
        return


    def setup_weather_app(self):
        logger.debug("Setup connection with external weather service")

        async def add_dao(app: Application):
            app.weather_app.setup_dao(app.dao)

        self.add_event_handler(event_type="startup", func=partial(add_dao, app=self))
        return OpenWeatherMap()

    def setup_openapi(self):

        async def add_openapi_schema(app: Application):
            if app.openapi_schema:
                return
            openapi_schema = get_openapi(
                title="OpenAgri Weather service",
                version="2.5.0",
                summary="This is OpenAPI for OpenAgri Weather service",
                description="",
                routes=app.routes,
            )
            app.openapi_schema = openapi_schema

        self.add_event_handler(event_type="startup", func=partial(add_openapi_schema, app=self))
        return

    def setup_middlewares(self):

        self.add_middleware(TrustedHostMiddleware, allowed_hosts=config.EXTRA_ALLOWED_HOSTS)
        return