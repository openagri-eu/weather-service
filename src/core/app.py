from functools import partial
import logging
import os


import fastapi
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document

from src.core import config
from src.core.security import create_gk_jwt_tokens
from src import utils
from src.core.dao import Dao
from src.core.jobs import run_forecast_for_farm
from src.api.api import api_router
from src.api.auth import auth_router
from src.external_services.openweathermap import OpenWeatherMap
from src.services.gatekeeper_service import GatekeeperServiceClient
from src.services.farmcalendar_service import FarmCalendarServiceClient
from src.scheduler import scheduler, JobManager


logger = logging.getLogger(__name__)

class Application(fastapi.FastAPI):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dao = self.setup_dao()
        self.weather_app = self.setup_weather_app()
        self.setup_uavs()
        self.setup_routes()
        self.setup_openapi()
        self.setup_middlewares()
        self.setup_fc_jobs()


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

            await app.setup_authentication_tokens()
            gk_client = GatekeeperServiceClient(app)
            logging.debug("Obtained JWT token from gatekeeper: %s", app.state.access_token)

            service_directory = await gk_client.gk_service_directory()
            logging.debug("Fetched service directory: %s", service_directory)

            app_routes = utils.list_routes_from_routers([api_router])
            logging.debug("App routes: %s", app_routes)

            existing_endpoints = {entry["endpoint"]: entry for entry in service_directory}
            for route in app_routes:
                relative_path = route["path"].lstrip("/")
                if relative_path not in existing_endpoints:
                    service_data = {
                        "base_url": f"http://{config.WEATHER_SRV_HOSTNAME}:{config.WEATHER_SRV_PORT}/",
                        "service_name": "weather_data",
                        "endpoint": relative_path,
                        "methods": route["methods"],
                    }
                    response = await gk_client.gk_service_register(service_data)
                    logging.info("Registered new service: %s", response)

            await gk_client.gk_logout(app.state.refresh_token)


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

    def setup_uavs(self):
        logger.debug("Setup connection with external weather service")

        async def load_uavs_from_csv():
            csv_path = '/data/drone_registrations.csv'
            if os.path.isfile(csv_path):
                await utils.load_uavs_from_csv(csv_path)

        self.add_event_handler(event_type="startup", func=partial(load_uavs_from_csv))
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

    def setup_fc_jobs(self):

        async def start_scheduler(app: Application):
            job_manager = JobManager(scheduler, app)
            fc_client = FarmCalendarServiceClient(app)
            logger.debug("Scheduler started!")

            # Initial farm/parcel/machine sync
            app.resync_all_jobs(fc_client, job_manager)

            # Schedule nightly re-sync (every day at 03:00)
            scheduler.add_job(
                app.resync_all_jobs,
                trigger="cron",
                hour=3,
                id="daily_job_resync",
                args=[fc_client, job_manager]
            )

        self.add_event_handler(event_type="startup", func=partial(start_scheduler, app=self))
        return

    async def resync_farm_jobs(self, fc_client: FarmCalendarServiceClient, jm: JobManager):
        logger.debug("🔄 Resyncing farm forecast jobs...")
        farms = await fc_client.get_farms()
        jm.reschedule_all_farm_jobs(
            farms=farms,
            get_parcels=lambda farm_id: fc_client.get_parcels_for_farm,
            get_machines=lambda farm_id: fc_client.get_machines_for_farm,
            job_fn=run_forecast_for_farm
        )


    async def setup_authentication_tokens(self):
        self.state.access_token, self.state.refresh_token = await create_gk_jwt_tokens()
