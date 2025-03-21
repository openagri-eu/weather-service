from datetime import datetime, timezone
import logging
from typing import List, Optional

import httpx
from fastapi import HTTPException
from beanie.operators import In

from src.core import config
from src import utils
from src.core.dao import Dao
from src.external_services.interoperability import InteroperabilitySchema
from src.models.point import Point
from src.models.prediction import Prediction
from src.models.uav import FlyStatus, UAVModel
from src.models.weather_data import WeatherData
from src.core.exceptions import InvalidWeatherDataError, UAVModelNotFoundError
from src.schemas.uav import FlightForecastListResponse, FlightStatusForecastResponse


logger = logging.getLogger(__name__)

class SourceError(Exception):
   ...

class OpenWeatherMap():

    properties = {
        'service': 'openWeatherMaps',
        'operation': 'weatherForecast',
        'dataClassification': 'prediction',
        'dataType': 'weather',
        'endpointURI': 'http://api.openweathermap.org/data/2.5',
        'documentationURI': 'https://openweathermap.org/forecast5',
        'dataExpiration': 3000,
        'dataProximityRadius': 100,
        'extracted_schema': {
            'period': {
                'timestamp': ['dt'],
                # 'datetime': ['dt_txt'],
            },
            'measurements': {
                'ambient_temperature': ['main', 'temp'],
                'ambient_humidity': ['main', 'humidity'],
                'wind_speed': ['wind', 'speed'],
                'wind_direction': ['wind', 'deg'],
                'precipitation': ['rain', '3h'],
            }
        },
    }

    def __init__(self):
       self.dao = None

    def setup_dao(self, dao: Dao):
       self.dao = dao

    # Helper function to get weather predictions from DB or OpenWeatherMap
    async def get_predictions(self, lat: float, lon: float) -> list[Prediction]:
        try:
            predictions = await self.dao.find_predictions_for_point(lat, lon)
            if predictions:
                return predictions

            point = await self.dao.find_or_create_point(lat, lon)
            url = f'{self.properties["endpointURI"]}/forecast?units=metric&lat={lat}&lon={lon}&appid={config.OPENWEATHERMAP_API_KEY}'
            openweathermap_json = await utils.http_get(url)
            predictions = await self.parseForecast5dayResponse(point, openweathermap_json)
        except httpx.HTTPError as httpe:
            logger.exception(httpe)
            raise SourceError(f"Request to {httpe.request} was not successful")
        except Exception as e:
            logger.exception(e)
            raise e
        else:
            return predictions

    # Fetches the 5-day weather forecast for a given latitude and longitude.
    # Checks if the forecast is cached, otherwise fetches it from OpenWeatherMap.
    # If an error occurs, it raises a SourceError for HTTP errors or the original exception.
    # Returns the forecast Predictions.
    async def get_weather_forecast5days(self, lat: float, lon: float) -> dict:
        predictions = await self.get_predictions(lat, lon)
        return predictions

    # Fetches the 5-day weather forecast in Linked Data format for a given latitude and longitude.
    # Calls the get_weather_forecast5days method and transforms the data into JSON-LD format.
    # Raises an exception if anything goes wrong.
    # Returns the forecast data in linked-data (JSON-LD) format.
    async def get_weather_forecast5days_ld(self, lat: float, lon: float) -> dict:
        predictions = await self.get_predictions(lat, lon)
        point = await self.dao.find_point(lat, lon)
        jsonld_data = InteroperabilitySchema.predictions_to_jsonld(predictions, point)
        return jsonld_data

    # Fetches and calculates the Temperature-Humidity Index (THI) for a given latitude and longitude.
    # If the weather data is not cached, it fetches it from OpenWeatherMap and saved in the DB.
    # Raises a SourceError for HTTP errors or the original exception if any other error occurs.
    # Returns the calculated THI.
    async def get_thi(self, lat: float, lon: float) -> float:
        weather_data = await self.save_weather_data_thi(lat, lon)
        return weather_data

    # Fetches and calculates the Temperature-Humidity Index (THI) in Linked Data format
    # for a given latitude and longitude.
    # If the weather data is not cached, it fetches it from OpenWeatherMap and saved in the DB.
    # Raises a SourceError for HTTP errors or the original exception if any other error occurs.
    # Returns the calculated THI in linked-data (JSON-LD) format.
    async def get_thi_ld(self, lat: float, lon: float) -> dict:
        weather_data = await self.save_weather_data_thi(lat, lon)
        point = await self.dao.find_point(lat, lon)
        jsonld_data = InteroperabilitySchema.weather_data_to_jsonld(weather_data, point)
        return jsonld_data

    # Fetches the current weather data for a given latitude and longitude.
    # If the weather data is not cached, it fetches it from OpenWeatherMap and saved in the DB.
    # Raises a SourceError for HTTP errors or the original exception if any other error occurs.
    # Returns the weather data as a dictionary.
    async def get_weather(self, lat: float, lon: float) -> dict:
        weather_data = await self.save_weather_data_thi(lat, lon)
        return weather_data

    # Fetch weather forecast and calculates fligh conditions for UAV
    async def get_flight_forecast_for_all_uavs(
            self, lat: float, lon: float,
            uavmodels: Optional[List[str]] = None,
            status_filter: Optional[List[str]] = None
    ) -> dict:

        # Fetch all UAV models or filter by provided UAV list
        query = UAVModel.find()
        if uavmodels:
            query = query.find(In(UAVModel.model, uavmodels))

        uavs = await query.to_list()
        if not uavs:
            raise HTTPException(status_code=404, detail="No UAV models found")

        point = await self.dao.find_or_create_point(lat, lon)

        # Fetch weather data once (to avoid redundant API calls)
        try:
            url = f'{self.properties["endpointURI"]}/forecast?units=metric&lat={lat}&lon={lon}&appid={config.OPENWEATHERMAP_API_KEY}'
            forecast5 = await utils.http_get(url)
        except httpx.HTTPError as httpe:
            logger.exception(f"HTTP error while fetching weather data: {httpe}")
            raise HTTPException(status_code=502, detail="Error fetching weather data from OpenWeatherMap")

        if "list" not in forecast5:
            raise HTTPException(status_code=500, detail="Invalid weather data received")

        results = []
        for forecast in forecast5["list"]:
            forecast_time = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
            weather_data = {
                "temp": forecast["main"]["temp"],
                "wind": forecast["wind"]["speed"],
                "precipitation": forecast.get("pop", 0),
                "rain": forecast.get("rain", {}).get("3h", 0.0) / 3 # Convert mm/3h to mm/h
            }

            for uav in uavs:
                try:
                    status = await utils.evaluate_flight_conditions(uav, weather_data)
                except Exception as e:
                    logger.exception(f"Error evaluating flight conditions for {uav.model}: {e}")
                    continue

                # Apply filtering (if user wants only certain statuses)
                if status_filter and (status.value not in status_filter):
                    continue

                flight_data = FlightStatusForecastResponse(
                    timestamp=forecast_time.isoformat(),
                    uavmodel=uav.model,
                    status=status.value,
                    weather_source="OpenWeatherMap",
                    weather_params=weather_data,
                    location=point.location
                )
                results.append(flight_data)

        return FlightForecastListResponse(forecasts=results)


    async def get_flight_forecast_for_uav(self, lat: float, lon: float, uavmodel: str) -> dict:
        try:
            uav = await UAVModel.find_one(UAVModel.model == uavmodel)
            if not uav:
                raise HTTPException(status_code=404, detail="UAV model not found")

            # predictions = await self.dao.find_predictions_for_point(lat, lon)
            # if predictions:
            #     return predictions

            point = await self.dao.find_or_create_point(lat, lon)
            url = f'{self.properties["endpointURI"]}/forecast?units=metric&lat={lat}&lon={lon}&appid={config.OPENWEATHERMAP_API_KEY}'
            openweathermap_json = await utils.http_get(url)
            forecast5 = openweathermap_json
            if "list" not in forecast5:
                raise HTTPException(status_code=500, detail="Invalid weather data received")

            results = []
            for forecast in forecast5["list"]:
                forecast_time = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
                weather_data = {
                    "temp": forecast["main"]["temp"],
                    "wind": forecast["wind"]["speed"],
                    "precipitation": forecast.get("pop", 0),
                    "rain": forecast.get("rain", {}).get("3h", 0.0) / 3 # Convert mm/3h to mm/h
                }

                status = await utils.evaluate_flight_conditions(uav, weather_data)

                flight_data = FlyStatus(
                    timestamp=forecast_time,
                    uav_model=uav.model,
                    status=status.value,
                    weather_params=weather_data,
                    weather_source="OpenWeatherMap",
                    location=point.location.model_dump()
                )
                await flight_data.insert()

                results.append(FlightStatusForecastResponse(
                    timestamp=flight_data.timestamp.isoformat(),
                    uavmodel=uav.model,
                    status=status.value,
                    weather_source="OpenWeatherMap",
                    weather_params=weather_data,
                    location=point.location
                ))

        except httpx.HTTPError as httpe:
            logger.exception(httpe)
            raise SourceError(f"Request to {httpe.request.url} was not successful")
        except Exception as e:
            logger.exception(e)
            raise e

        return FlightForecastListResponse(forecasts=results)



    # Asynchronously fetches weather data from the OpenWeatherMap API for a given latitude and longitude.
    # Calculates the Temperature-Humidity Index (THI), and stores the weather data along with the THI in the database.
    async def save_weather_data_thi(self, lat: float, lon: float) -> WeatherData:
        try:
            weather_data = await self.dao.find_weather_data_for_point(lat, lon)
            if weather_data:
                return weather_data

            point = await self.dao.find_or_create_point(lat, lon)
            url = f'{self.properties["endpointURI"]}/weather?units=metric&lat={lat}&lon={lon}&appid={config.OPENWEATHERMAP_API_KEY}'
            openweathermap_json = await utils.http_get(url)
            temp = openweathermap_json["main"]["temp"]
            rh = openweathermap_json["main"]["humidity"]
            thi = utils.calculate_thi(temp, rh)
        except httpx.HTTPError as httpe:
            logger.exception(httpe)
            raise SourceError(f"Request to {httpe.request.url} was not successful")
        except Exception as e:
            logger.exception(e)
            raise e

        return await self.dao.save_weather_data_for_point(point, data=openweathermap_json, thi=thi)

    async def ensure_forecast_for_uavs_and_location(self, uav_model_names: List[str], lat: float, lon: float) -> List[FlyStatus]:
        point = await self.dao.find_or_create_point(lat, lon)

        # Fetch all matching UAV models
        uavs = await UAVModel.find(UAVModel.model.in_(uav_model_names)).to_list()

        # Map found UAVs for quick lookup
        uav_lookup = {uav.model: uav for uav in uavs}
        missing_uavs = [model for model in uav_model_names if model not in uav_lookup]

        if missing_uavs:
            raise UAVModelNotFoundError(f"UAV models not found: {', '.join(missing_uavs)}")

        now = datetime.now(timezone.utc)
        results = []

        # Check if any model needs forecast data
        models_to_fetch = []
        for model in uav_model_names:
            existing = await FlyStatus.find(
                (FlyStatus.uav_model == model) &
                (FlyStatus.location == point.location) &
                (FlyStatus.timestamp > now)
            ).to_list()
            if not existing:
                models_to_fetch.append(model)
            else:
                results.extend(existing)

        # If no models need data, return what we found
        if not models_to_fetch:
            return results

        # Fetch forecast from OpenWeatherMap only once
        url = f'{self.properties["endpointURI"]}/forecast?units=metric&lat={lat}&lon={lon}&appid={config.OPENWEATHERMAP_API_KEY}'
        openweathermap_json = await utils.http_get(url)
        forecast5 = openweathermap_json

        if "list" not in forecast5:
            raise InvalidWeatherDataError()

        for forecast in forecast5["list"]:
            forecast_time = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

            weather_data = {
                "temp": forecast["main"]["temp"],
                "wind": forecast["wind"]["speed"],
                "precipitation": forecast.get("pop", 0),
                "rain": forecast.get("rain", {}).get("3h", 0.0) / 3
            }

            # Evaluate for each UAV model
            for model in models_to_fetch:
                uav = uav_lookup[model]
                status = await utils.evaluate_flight_conditions(uav, weather_data)

                flight_data = FlyStatus(
                    timestamp=forecast_time,
                    uav_model=model,
                    status=status.value,
                    weather_params=weather_data,
                    weather_source="OpenWeatherMap",
                    location=point.location.model_dump()
                )
                await flight_data.insert()
                results.append(flight_data)

        return results

    # Parses the 5-day forecast data and extracts useful predictions based on the provided schema.
    # For each forecast period, it creates and saves Prediction objects in the database.
    # Logs any errors that occur during the transformation process.
    # Returns a list of predictions.
    async def parseForecast5dayResponse(self, point: Point, data: dict) -> list:
        # Extract data to a list of Predictions
        extracted_data = []
        predictions = []
        try:
            for e in data['list']:
                extracted_element = utils.deepcopy_dict(self.properties['extracted_schema'])
                for key, path in self.properties['extracted_schema']['period'].items():
                    extracted_element['period'][key] = utils.extract_value_from_dict_path(e, path)
                for key, path in self.properties['extracted_schema']['measurements'].items():
                    extracted_element['measurements'][key] = utils.extract_value_from_dict_path(e, path)
                    if not extracted_element['measurements'][key]:
                        continue
                    prediction = await Prediction(
                        value=extracted_element['measurements'][key],
                        measurement_type=key,
                        timestamp=extracted_element['period']['timestamp'],
                        data_type='weather',
                        source='openweathermaps',
                        spatial_entity=point
                        ).create()
                    predictions.append(prediction)
                    extracted_data.append(extracted_element)
        except Exception as e:
            logger.debug("Cannot transform to Linked Data")
            logger.error(e)
        else:
            return predictions


