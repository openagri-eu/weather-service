from fastapi import HTTPException
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from tests.fixtures import *
from datetime import datetime, timedelta


from httpx import HTTPError

from src.external_services import openweathermap
from src.external_services.openweathermap import SourceError
from src.models.prediction import Prediction
from src.models.point import Point
from src.models.weather_data import WeatherData


class TestOpenWeatherMap:

    # Test when cached predictions are available.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_cached_predictions(
        self, openweathermap_srv
    ):
        predictions = [
            Prediction(
                value=42,
                measurement_type="type",
                timestamp=datetime.now(),
                data_type="weather",
                source="openweathermaps",
                spatial_entity=Point(type="station"),
            )
        ]
        openweathermap_srv.dao.find_predictions_for_point.return_value = predictions
        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_weather_forecast5days(lat, lon)
        assert isinstance(result, list)
        assert result[0] == predictions[0].model_dump(
            include={
                "value": True,
                "timestamp": True,
                "measurement_type": True,
                "source": True,
                "spatial_entity": {"location": {"coordinates"}},
            }
        )

    # Test when no cached predictions are found.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_non_cached_prediction(
        self, openweathermap_srv
    ):
        prediction = Prediction(
            value=42,
            measurement_type="type",
            timestamp=datetime.now(),
            data_type="weather",
            source="openweathermaps",
            spatial_entity=Point(type="station"),
        )

        openweathermap_srv.dao.find_predictions_for_point.return_value = []
        openweathermap_srv.dao.create_point.return_value = Point(type="station")

        mock_get = AsyncMock(return_value={})
        openweathermap.utils.http_get = mock_get

        mock_parseForecast5dayResponse = AsyncMock(return_value=[prediction])
        openweathermap_srv.parseForecast5dayResponse = mock_parseForecast5dayResponse

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_weather_forecast5days(lat, lon)
        assert isinstance(result, list)
        assert result[0] == prediction.model_dump(
            include={
                "value": True,
                "timestamp": True,
                "measurement_type": True,
                "source": True,
                "spatial_entity": {"location": {"coordinates"}},
            }
        )


    # Test when cached predictions are available and created within the last 3 hours (Should Pass)
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_recent_predictions(self, openweathermap_srv):
        recent_prediction = Prediction(
            value=42,
            measurement_type="type",
            timestamp=datetime.now(),
            created_at=datetime.now() - timedelta(hours=2, minutes=30),  # Within 3 hours
            data_type='weather',
            source='openweathermaps',
            spatial_entity=Point(type="station")
        )

        openweathermap_srv.dao.find_predictions_for_point.return_value = [recent_prediction]
        lat, lon = (42.424242, 24.242424)

        result = await openweathermap_srv.get_weather_forecast5days(lat, lon)

        assert isinstance(result, list)
        assert len(result) > 0  # Ensure a prediction is returned
        assert result[0] == recent_prediction.model_dump(include={
            'value': True,
            'timestamp': True,
            'measurement_type': True,
            'source': True,
            'spatial_entity': {'location': {'coordinates'}}
        })


    # Test when cached predictions are older than 3 hours (Should Fail)
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_old_predictions(self, openweathermap_srv):
        old_prediction = Prediction(
            value=42,
            measurement_type="type",
            timestamp=datetime.now(),
            created_at=datetime.now() - timedelta(hours=3, minutes=1),  # Just over 3 hours
            data_type='weather',
            source='openweathermaps',
            spatial_entity=Point(type="station")
        )
        new_prediction = Prediction(
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

        mock_parseForecast5dayResponse = AsyncMock(return_value=[new_prediction])
        openweathermap_srv.parseForecast5dayResponse = mock_parseForecast5dayResponse

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_weather_forecast5days(lat, lon)

        assert isinstance(result, list)
        assert len(result) == 1  # No predictions should be returned since it's too old


    # Test if the service raises a SourceError when the HTTP request fails.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_http_get_throws_error(
        self, openweathermap_srv
    ):
        openweathermap_srv.dao.find_predictions_for_point.return_value = []
        openweathermap_srv.dao.create_point.return_value = Point(type="station")

        error = HTTPError("Http error")
        error.request = type("Request", (object,), dict({"url": "http://test.url"}))
        mock_get = AsyncMock(side_effect=error)
        openweathermap.utils.http_get = mock_get

        lat, lon = (42.424242, 24.242424)
        with pytest.raises(SourceError):
            await openweathermap_srv.get_weather_forecast5days(lat, lon)

    # Test if a generic exception during response parsing is caught.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_cathes_generic_exception(
        self, openweathermap_srv
    ):
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
            data_type="weather",
            source="openweathermaps",
            spatial_entity=Point(type="station"),
        )
        openweathermap_srv.dao.find_predictions_for_point.return_value = [prediction]
        openweathermap_srv.dao.find_point.return_value = Point(type="station")

        mock = MagicMock(
            return_value={
                "@context": {},
            }
        )
        openweathermap.InteroperabilitySchema.predictions_to_jsonld = mock

        lat, lon = (42.424242, 24.242424)

        result = await openweathermap_srv.get_weather_forecast5days_ld(lat, lon)
        assert isinstance(result, dict)
        assert "@context" in result

    # Test exception handling for get_weather_forecast5days_ld.
    @pytest.mark.anyio
    async def test_get_weather_forecast5days_ld_catches_exception(
        self, openweathermap_srv
    ):
        openweathermap_srv.dao.find_predictions_for_point.side_effect = Exception

        lat, lon = (42.424242, 24.242424)
        with pytest.raises(Exception):
            await openweathermap_srv.get_weather_forecast5days_ld(lat, lon)

    # Test the weather data retrieval for a specific location.
    @pytest.mark.anyio
    async def test_get_weather(self, openweathermap_srv):
        weather_data = WeatherData(
            data={"main": {"temp": 42.0}}, spatial_entity=Point(type="station")
        )
        openweathermap_srv.dao.find_weather_data_for_point.return_value = weather_data

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_weather(lat, lon)
        assert isinstance(result, dict)
        assert result["data"]["main"]["temp"] == 42.0

    # Test the THI (Temperature Humidity Index) from cached data.
    @pytest.mark.anyio
    async def test_get_thi_from_cached_weather_data(self, openweathermap_srv):
        weather_data = WeatherData(
            data={"main": {"temp": 42.0, "humidity": 24.42}},
            spatial_entity=Point(type="station"),
            thi=86.74,
        )
        openweathermap_srv.dao.find_weather_data_for_point.return_value = weather_data

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_thi(lat, lon)
        assert isinstance(result, dict)
        assert result["thi"] == 86.74

    # Test that weather data is considered recent if created within the last 3 hours.
    @pytest.mark.anyio
    async def test_get_weather_recent_data(self, openweathermap_srv):
        weather_data = WeatherData(
            data={'main': {'temp': 42.0}},
            spatial_entity=Point(type="station"),
            created_at=datetime.utcnow() - timedelta(hours=2, minutes=30)  # 2.5 hours ago (Valid)
        )
        openweathermap_srv.dao.find_weather_data_for_point.return_value = weather_data

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_weather(lat, lon)

        assert isinstance(result, dict)
        assert result['data']['main']['temp'] == 42.0
        assert (datetime.utcnow() - weather_data.created_at).total_seconds() <= 3 * 3600  # Within 3 hours

    # Test that weather data is considered outdated if created more than 3 hours ago.
    @pytest.mark.anyio
    async def test_get_weather_old_data(self, openweathermap_srv):
        weather_data = WeatherData(
            data={'main': {'temp': 42.0}},
            spatial_entity=Point(type="station"),
            created_at=datetime.utcnow() - timedelta(hours=4)  # 4 hours ago (Invalid)
        )
        new_weather_data = WeatherData(
            data={'main': {'temp': 43.0}},
            spatial_entity=Point(type="station"),
            created_at=datetime.utcnow()
        )

        openweathermap_srv.dao.find_weather_data_for_point.return_value = None
        openweathermap_srv.dao.create_point.return_value = Point(type="station")
        openweathermap_srv.dao.save_weather_data_for_point.return_value = new_weather_data

        mock_get = AsyncMock(return_value={"main": {"temp": 43.0, "humidity": 0.1}})
        openweathermap.utils.http_get = mock_get

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_weather(lat, lon)

        assert isinstance(result, dict)
        assert result['data']['main']['temp'] == 43.0
        assert (datetime.utcnow() - weather_data.created_at).total_seconds() > 3 * 3600  # More than 3 hours

    # Test the THI (Temperature Humidity Index) JSON-LD.
    @pytest.mark.anyio
    async def test_get_thi_ld(self, openweathermap_srv):
        weather_data = WeatherData(
            data={"main": {"temp": 42.0, "humidity": 24.42}, "dt": 1730201901},
            spatial_entity=Point(type="station"),
            thi=86.74,
        )
        openweathermap_srv.dao.find_weather_data_for_point.return_value = weather_data

        lat, lon = (42.424242, 24.242424)
        result = await openweathermap_srv.get_thi_ld(lat, lon)
        assert isinstance(result, dict)
        assert result["@graph"][0]["hasMember"][0]["hasResult"]["numericValue"] == 86.74

    @pytest.mark.anyio
    @patch(
        "src.external_services.openweathermap.UAVModel.find_one", new_callable=AsyncMock
    )
    async def test_get_flight_forecast_for_uav(
        self,
        mock_find_one,
        async_client,
        mock_uav,
        mock_weather_data,
        openweathermap_srv,
    ):
        mock_find_one.return_value = mock_uav
        mock_get = AsyncMock(return_value=mock_weather_data)
        openweathermap.utils.http_get = mock_get
        openweathermap_srv.dao.create_point.return_value = Point(
            type="station", location={"type": "Point", "coordinates": [42.2, 24.24]}
        )

        response = await async_client.get(
            "/api/data/flight_forecast5/DJI?lat=52.0&lon=13.0"
        )
        assert response.status_code == 200
        data = response.json()
        assert "forecasts" in data
        assert len(data["forecasts"]) > 0
        assert data["forecasts"][0]["uavmodel"] == "DJI"

    @pytest.mark.anyio
    @patch(
        "src.external_services.openweathermap.UAVModel.find_one", new_callable=AsyncMock
    )
    async def test_get_flight_forecast_for_uavs(
        self,
        mock_find_one,
        async_client,
        mock_uav,
        mock_weather_data,
        openweathermap_srv,
    ):
        mock_find_one.return_value = mock_uav
        mock_get = AsyncMock(return_value=mock_weather_data)
        openweathermap.utils.http_get = mock_get
        openweathermap_srv.dao.create_point.return_value = Point(
            type="station", location={"type": "Point", "coordinates": [42.2, 24.24]}
        )

        response = await async_client.get(
            "/api/data/flight_forecast5/DJI?lat=52.0&lon=13.0"
        )
        assert response.status_code == 200
        data = response.json()
        assert "forecasts" in data
        assert len(data["forecasts"]) > 0
        assert data["forecasts"][0]["uavmodel"] == "DJI"

    @pytest.mark.anyio
    @patch("src.external_services.openweathermap.UAVModel.find")
    async def test_get_flight_forecast_for_all_uavs(
        self, mock_find, async_client, openweathermap_srv, mock_uav, mock_weather_data
    ):
        mock_find.return_value.to_list = AsyncMock(return_value=[mock_uav])
        mock_get = AsyncMock(return_value=mock_weather_data)
        openweathermap.utils.http_get = mock_get
        openweathermap_srv.dao.create_point.return_value = Point(
            type="station", location={"type": "Point", "coordinates": [42.2, 24.24]}
        )

        response = await async_client.get(
            "/api/data/flight_forecast5?lat=52.0&lon=13.0&status_filter=Marginally OK"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["forecasts"]) == 1
        assert data["forecasts"][0]["status"] == "Marginally OK"
