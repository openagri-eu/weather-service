from fastapi import HTTPException
import pytest
from unittest.mock import MagicMock, AsyncMock
from tests.fixtures import *
from datetime import datetime

from httpx import HTTPError

from src.external_services import openweathermap
from src.external_services.openweathermap import SourceError
from src.models.prediction import Prediction
from src.models.point import Point
from src.models.weather_data import WeatherData


class TestOpenWeatherMap:

    # Test when cached predictions are available.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_cached_predictions(self, openweathermap_srv):
        openweathermap_srv.dao.find_predictions_for_point.return_value = [
            Prediction(
                value=42,
                measurement_type="type",
                timestamp=datetime.now(),
                data_type='weather',
                source='openweathermaps',
                spatial_entity=Point(type="station")
            )
        ]
        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_weather_forecast5days(lat, lon)
        assert isinstance(result, list)
        assert isinstance(result[0], Prediction)

    # Test when no cached predictions are found.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_non_cached_prediction(self, openweathermap_srv):
        prediction = Prediction(
                value=42,
                measurement_type="type",
                timestamp=datetime.now(),
                data_type='weather',
                source='openweathermaps',
                spatial_entity=Point(type="station")
        )

        openweathermap_srv.dao.find_predictions_for_point.return_value = []
        openweathermap_srv.dao.create_point.return_value = Point(type="station")

        mock_get = AsyncMock(return_value={})
        openweathermap.utils.http_get = mock_get

        mock_parseForecast5dayResponse = AsyncMock(return_value=[prediction])  # Mock the response parsing
        openweathermap_srv.parseForecast5dayResponse = mock_parseForecast5dayResponse

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_weather_forecast5days(lat, lon)
        assert isinstance(result, list)
        assert result[0] == prediction.model_dump(include={
                                'value': True,
                                'timestamp': True,
                                'measurement_type': True,
                                'source': True,
                                'spatial_entity': {'location': {'coordinates'}}
                            })

    # Test if the service raises a SourceError when the HTTP request fails.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_http_get_throws_error(self, openweathermap_srv):
        openweathermap_srv.dao.find_predictions_for_point.return_value = []
        openweathermap_srv.dao.create_point.return_value = Point(type="station")

        error = HTTPError("Http error")
        error.request = type('Request', (object,), dict( {'url': 'http://test.url'}))
        mock_get = AsyncMock(side_effect=error)
        openweathermap.utils.http_get = mock_get

        lat, lon = (42.424242, 24.242424)
        with pytest.raises(SourceError):
            await openweathermap_srv.get_weather_forecast5days(lat, lon)

    # Test if a generic exception during response parsing is caught.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_cathes_generic_exception(self, openweathermap_srv):
        openweathermap_srv.dao.find_predictions_for_point.return_value = []
        openweathermap_srv.dao.create_point.return_value = Point(type="station")

        mock = AsyncMock(side_effect=Exception)
        openweathermap_srv.parseForecast5dayResponse = mock

        lat, lon = (42.424242, 24.242424)
        with pytest.raises(Exception):
            await openweathermap_srv.get_weather_forecast5days(lat, lon)

    # Test the service’s LD (Linked Data) response.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_ld(self, openweathermap_srv):
        prediction = Prediction(
                value=42,
                measurement_type="type",
                timestamp=datetime.now(),
                data_type='weather',
                source='openweathermaps',
                spatial_entity=Point(type="station")
        )
        openweathermap_srv.dao.find_predictions_for_point.return_value = [prediction]
        openweathermap_srv.dao.find_point.return_value = Point(type="station")

        mock = MagicMock(
            return_value={
                '@context': {},
                '@id': '',
            'collections': []
        })
        openweathermap.InteroperabilitySchema.predictions_to_jsonld = mock

        lat, lon = (42.424242, 24.242424)
        with pytest.raises(HTTPException):
            await openweathermap_srv.get_weather_forecast5days_ld(lat, lon)

        # TODO: Implement when OCSM for weather is ready
        # result = await openweathermap_srv.get_weather_forecast5days_ld(lat, lon)
        # assert isinstance(result, dict)
        # assert '@context' in result

    # Test exception handling for get_weather_forecast5days_ld.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_ld_catches_exception(self, openweathermap_srv):
        openweathermap_srv.dao.find_predictions_for_point.side_effect = Exception

        lat, lon = (42.424242, 24.242424)
        with pytest.raises(Exception):
            await openweathermap_srv.get_weather_forecast5days_ld(lat, lon)

    # Test the weather data retrieval for a specific location.
    @pytest.mark.anyio
    async def test_get_weather(self, openweathermap_srv):
        weather_data = WeatherData(
            data={'main': {'temp': 42.0}},
            spatial_entity=Point(type="station")
        )
        openweathermap_srv.dao.find_weather_data_for_point.return_value = weather_data

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_weather(lat, lon)
        assert isinstance(result, dict)
        assert result['data']['main']['temp'] == 42.0

    # Test the THI (Temperature Humidity Index) from cached data.
    @pytest.mark.anyio
    async def test_get_thi_from_cached_weather_data(self, openweathermap_srv):
        weather_data = WeatherData(
            data={'main': {'temp': 42.0, 'humidity': 24.42}},
            spatial_entity=Point(type="station"),
            thi=86.74
        )
        openweathermap_srv.dao.find_weather_data_for_point.return_value = weather_data

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_thi(lat, lon)
        assert isinstance(result, dict)
        assert result['thi'] == 86.74


