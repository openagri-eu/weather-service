from unittest.mock import AsyncMock
import pytest
from mongomock_motor import AsyncMongoMockClient
from httpx import AsyncClient
from beanie import init_beanie, Document

from src.core.dao import Dao
from src.external_services.openweathermap import OpenWeatherMap
from src.main import create_app
from src.api.api import api_router
import src.utils as utils


@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
async def openweathermap_srv():

    dao_mock = AsyncMock()
    owm_srv = OpenWeatherMap()
    owm_srv.setup_dao(dao_mock)
    yield owm_srv


@pytest.fixture
async def app():
    _app = create_app()
    _app.include_router(api_router)

    # Mock the MongoDB client
    mongodb_client = AsyncMongoMockClient()
    mongodb = mongodb_client["test_database"]
    _app.dao = Dao(mongodb_client)
    await init_beanie(
                database=mongodb,
                document_models=utils.load_classes('**/models/**.py', (Document,))
            )

    mock = AsyncMock()
    mock.get_weather_forecast5days.return_value = {"forecast": "mocked_data"}
    mock.get_weather_forecast5days_ld.return_value = {"forecast": "mocked_data"}
    mock.get_weather.return_value = {"forecast": "mocked_data"}
    mock.get_thi.return_value = {"forecast": "mocked_data"}
    _app.weather_app = mock

    yield _app


@pytest.fixture
async def async_client(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
