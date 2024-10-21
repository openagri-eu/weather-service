import logging

import httpx
from fastapi import HTTPException

from src.core import config
from src import utils
from src.core.dao import Dao
from src.models.point import Point
from src.models.prediction import Prediction
from src.interoperability import InteroperabilitySchema
from src.models.weather_data import WeatherData


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

            point = await self.dao.create_point(lat, lon)
            url = f'{self.properties["endpointURI"]}/forecast?units=metric&lat={lat}&lon={lon}&appid={config.OPENWEATHERMAP_API_KEY}'
            openweathermap_json = await utils.http_get(url)
            predictions = await self.parseForecast5dayResponse(point, openweathermap_json)
        except httpx.HTTPError as httpe:
            logger.exception(httpe)
            raise SourceError(f"Request to {httpe.request.url} was not successful")
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
        return [p.model_dump(
                        include={
                            'value': True,
                            'timestamp': True,
                            'measurement_type': True,
                            'source': True,
                            'spatial_entity': {'location': {'coordinates'}}
                        }
                    ) for p in predictions]

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
        return weather_data.model_dump(
                                include={
                                    'spatial_entity': {'location': 'coordinates'},
                                    'thi': True,
                                    'data': {'dt': True}
                                }
                            )

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
        return weather_data.model_dump(
                                include={
                                    'spatial_entity': {'location': 'coordinates'},
                                    'data': {
                                        'weather': {0: 'description'},
                                        'main': {'temp', 'humidity', 'pressure'},
                                        'wind': {'speed'}, 'dt': True
                                    }
                                }
                            )

    # Asynchronously fetches weather data from the OpenWeatherMap API for a given latitude and longitude.
    # Calculates the Temperature-Humidity Index (THI), and stores the weather data along with the THI in the database.
    async def save_weather_data_thi(self, lat: float, lon: float) -> WeatherData:
        try:
            weather_data = await self.dao.find_weather_data_for_point(lat, lon)
            if weather_data:
                return weather_data

            point = await self.dao.create_point(lat, lon)
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


