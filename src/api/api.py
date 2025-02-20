import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, Request, HTTPException

from src.api.deps import authenticate_request

from src.schemas.prediction import PredictionOut
from src.schemas.uav import FlightForecastListResponse
from src.schemas.weather_data import THIDataOut, WeatherDataOut


logger = logging.getLogger(__name__)

api_router = APIRouter()


# Fetches the 5-day weather forecast for a given latitude and longitude.
# If an error occurs, a 500 HTTP exception is raised.
# Returns the forecast data if successful.
@api_router.get("/api/data/forecast5", response_model=list[PredictionOut])
async def get_weather_forecast5days(
    request: Request,
    lat: float,
    lon: float,
    payload: dict = Depends(authenticate_request),
):
    try:
        result = await request.app.weather_app.get_weather_forecast5days(lat, lon)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500)
    else:
        return result


# Fetches the 5-day weather forecast in JSON-LD format for a given latitude and longitude.
# If an error occurs, a 500 HTTP exception is raised.
# Returns the forecast data in json-ld format if successful.


@api_router.get("/api/linkeddata/forecast5")
async def get_weather_forecast5days_ld(
    request: Request,
    lat: float,
    lon: float,
    payload: dict = Depends(authenticate_request),
):
    try:
        result = await request.app.weather_app.get_weather_forecast5days_ld(lat, lon)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        return result


# Fetches the current weather data for a given latitude and longitude.
# If an error occurs, a 500 HTTP exception is raised.
# Returns the weather data if successful.


@api_router.get("/api/data/weather", response_model=WeatherDataOut, response_model_include={
                                    'id': True,
                                    'spatial_entity': True,
                                    'data': {
                                        'weather': {0: 'description'},
                                        'main': {'temp', 'humidity', 'pressure'},
                                        'wind': {'speed'}, 'dt': True
                                    }
                                })
async def get_weather(
    request: Request,
    lat: float,
    lon: float,
    payload: dict = Depends(authenticate_request),
):
    try:
        result = await request.app.weather_app.get_weather(lat, lon)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        return result


# Calculates the current Temperature-Humidity Index (THI) for a given latitude and longitude.
# If an error occurs, a 500 HTTP exception is raised.
# Returns the THI data if successful.


@api_router.get("/api/data/thi", response_model=THIDataOut)
async def get_thi(
    request: Request,
    lat: float,
    lon: float,
    payload: dict = Depends(authenticate_request),
):
    try:
        result = await request.app.weather_app.get_thi(lat, lon)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500)
    else:
        return result


# Calculates the current Temperature-Humidity Index (THI) for a given latitude and longitude.
# If an error occurs, a 500 HTTP exception is raised.
# Returns the THI data if successful.


@api_router.get("/api/linkeddata/thi")
async def get_thi_ld(
    request: Request,
    lat: float,
    lon: float,
    payload: dict = Depends(authenticate_request),
):
    try:
        result = await request.app.weather_app.get_thi_ld(lat, lon)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500)
    else:
        return result


# Forecasts suitable UAV flight conditions for all drones
@api_router.get("/api/data/flight_forecast5", response_model=FlightForecastListResponse)
async def get_flight_forecast_for_all_uavs(
    request: Request,
    lat: float,
    lon: float,
    uavmodels: Annotated[list[str] | None, Query()] = None,
    status_filter: Annotated[list[str] | None, Query()] = None,
    payload: dict = Depends(authenticate_request),
):
    try:
        result = await request.app.weather_app.get_flight_forecast_for_all_uavs(lat, lon, uavmodels, status_filter)
    except Exception as e:
        logger.exception(e)
        raise e
    else:
        return result

@api_router.get("/api/data/flight_forecast5/{uavmodel}", response_model=FlightForecastListResponse)
async def get_flight_forecast_for_uav(request: Request, lat: float, lon: float, uavmodel: str, payload: dict = Depends(authenticate_request),
):
    try:
        result = await request.app.weather_app.get_flight_forecast_for_uav(lat, lon, uavmodel)
    except Exception as e:
        logger.exception(e)
        raise e
    else:
        return result

