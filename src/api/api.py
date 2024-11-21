from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import authenticate_request


logger = logging.getLogger(__name__)

api_router = APIRouter()

class WeatherQueryParams(BaseModel):
    lat: float = Field(..., description="Latitude of the location (-90 to 90)")
    lon: float = Field(..., description="Longitude of the location (-180 to 180)")
    from_time: Optional[datetime] = Field(None, alias="from", description="Start time (ISO 8601 format)")
    to_time: Optional[datetime] = Field(None, alias="to", description="End time (ISO 8601 format)")

# Fetches the 5-day weather forecast for a given latitude and longitude.
# If an error occurs, a 500 HTTP exception is raised.
# Calculate spray indicator
# Returns an array of (indication, timestamp).
@api_router.get("/api/data/historical-labels")
async def get_historical_labels(
    request: Request,
    query_params: WeatherQueryParams = Depends(),
    payload: dict = Depends(authenticate_request)
):
    try:
        result = await request.app.weather_app.get_historical_labels(
            query_params.lat,
            query_params.lon,
            query_params.from_time,
            query_params.to_time
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500)
    else:
        return result

# Fetches the 5-day weather forecast for a given latitude and longitude.
# If an error occurs, a 500 HTTP exception is raised.
# Returns the forecast data if successful.
@api_router.get("/api/data/forecast5")
async def get_weather_forecast5days(
    request: Request,
    query_params: WeatherQueryParams = Depends(),
    payload: dict = Depends(authenticate_request)
):
    try:
        result = await request.app.weather_app.get_weather_forecast5days(query_params.lat, query_params.lon)
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
    query_params: WeatherQueryParams = Depends(),
    payload: dict = Depends(authenticate_request)
):
    try:
        result = await request.app.weather_app.get_weather_forecast5days_ld(query_params.lat, query_params.lon)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        return result

# Fetches the current weather data for a given latitude and longitude.
# If an error occurs, a 500 HTTP exception is raised.
# Returns the weather data if successful.
@api_router.get("/api/data/weather")
async def get_weather(
    request: Request,
    query_params: WeatherQueryParams = Depends(),
    payload: dict = Depends(authenticate_request)
):
    try:
        result = await request.app.weather_app.get_weather(query_params.lat, query_params.lon)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        return result

# Calculates the current Temperature-Humidity Index (THI) for a given latitude and longitude.
# If an error occurs, a 500 HTTP exception is raised.
# Returns the THI data if successful.
@api_router.get("/api/data/thi")
async def get_thi(
    request: Request,
    query_params: WeatherQueryParams = Depends(),
    payload: dict = Depends(authenticate_request)
):
    try:
        result = await request.app.weather_app.get_thi(query_params.lat, query_params.lon)
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
    query_params: WeatherQueryParams = Depends(),
    payload: dict = Depends(authenticate_request)
):
    try:
        result = await request.app.weather_app.get_thi_ld(query_params.lat, query_params.lon)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500)
    else:
        return result
