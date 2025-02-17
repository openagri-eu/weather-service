from datetime import datetime, timedelta
from unittest.mock import AsyncMock
import jwt
import pytest
from mongomock_motor import AsyncMongoMockClient
from httpx import AsyncClient
from beanie import init_beanie, Document

from src.core import config
from src.core.dao import Dao
from src.external_services.openweathermap import OpenWeatherMap
from src.main import create_app
from src.api.api import api_router
from src.models.uav import UAVModel
from src.schemas.uav import FlightForecastListResponse, FlightStatusForecastResponse
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
async def app(openweathermap_srv):
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
    # mock.get_weather_forecast5days.return_value = {"forecast": "mocked_data"}
    # mock.get_weather_forecast5days_ld.return_value = {"forecast": "mocked_data"}
    # mock.get_weather.return_value = {"forecast": "mocked_data"}
    # mock.get_thi.return_value = {"forecast": "mocked_data"}
    # _app.weather_app = mock
    _app.weather_app = openweathermap_srv


    yield _app

@pytest.fixture
def test_jwt_token():
    """Generate a valid JWT token for testing."""
    payload = {
        "sub": "test_user",
        "exp": datetime.utcnow() + timedelta(hours=1),  # Token valid for 1 hour
        "roles": ["user"],  # Include any necessary claims
    }
    token = jwt.encode(payload, config.KEY, algorithm=config.ALGORITHM)
    return token

@pytest.fixture
async def async_client(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_uav(app):
    return UAVModel(
        model="DJI", manufacturer="MANU",
        max_wind_speed=10.0, min_operating_temp=-10.0,
        max_operating_temp=40.0, precipitation_tolerance=42.0
    )


@pytest.fixture
def mock_weather_data(app):
    now = datetime.utcnow()
    return {
        "cod": "200",
        "list": [
            {
                "dt_txt": (now + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
                "main": {"temp": 10, "feels_like": 8},
                "wind": {"speed": 5},
                "pop": 0.1,
                "weather": [{"description": "clear sky"}],
            }
        ],
    }


@pytest.fixture
def mock_flight_response():
    """Mock flight forecast response"""
    return FlightForecastListResponse(
        forecasts=[
            FlightStatusForecastResponse(
                timestamp=datetime.utcnow().isoformat(),
                uavmodel="DJI",
                status="SAFE",
                weather_source="OpenWeatherMap",
                weather_params={"temp": 10, "wind": 5, "precipitation": 0.1},
                location={"type": "Point", "coordinates": [52.0, 13.0]}
            )
        ]
    )
