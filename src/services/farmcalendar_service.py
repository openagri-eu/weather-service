import json
import re
import time
from typing import Optional, Tuple
from uuid import uuid4
from fastapi import FastAPI, HTTPException
import logging

import backoff

from src.core import config
from src import utils
from src.services.base import MicroserviceClient
from src.services.interoperability import MadeBySensorSchema, ObservationSchema, QuantityValueSchema


logger = logging.getLogger(__name__)

class FarmCalendarServiceClient(MicroserviceClient):

    def __init__(self, app: FastAPI):
        super().__init__(base_url=config.FARM_CALENDAR_URL, service_name="Farm Calendar", app=app)

    async def fetch_or_create_activity_type(self, activity_type: str, description: str) -> str:
        act_jsonld = await self.get(f'/api/v1/FarmCalendarActivityTypes/?name={activity_type}')

        if not self._get_activity_type_id(act_jsonld):
            json_payload = {
                "name": activity_type,
                "description": description,
            }
            act_jsonld = await self.post('/api/v1/FarmCalendarActivityTypes/', json=json_payload)

        return self._get_activity_type_id(act_jsonld)

    # Create THI Observation Activity Type
    async def fetch_or_create_thi_activity_type(self) -> str:
        self.thi_activity_type = await self.fetch_or_create_activity_type(
            'THI_Observation',
            'Activity type collecting observed values for Temperature Humidity Index'
        )

    # Create Flight Forecast Observation Activity Type
    async def fetch_or_create_flight_forecast_activity_type(self) -> str:
        self.ff_activity_type = await self.fetch_or_create_activity_type(
            'Flight_Forecast_Observation',
            'Activity type collecting observed values for UAV Flight Forecast'
        )

    # Create spray conditions forecast Observation Activity Type
    async def fetch_or_create_spray_forecast_activity_type(self) -> str:
        self.sp_activity_type = await self.fetch_or_create_activity_type(
            'Spray_Forecast_Observation',
            'Activity type collectins observed values for spray conditions forecast'
        )

    def _get_activity_type_id(self, jsonld: dict) -> Optional[str]:
        if jsonld['@graph']:
            return jsonld["@graph"][0]["@id"]
        return

    # Fetch locations from FARM_CALENDAR_URI
    async def fetch_locations(self):
        response = await self.get('/api/v1/FarmParcels/')

        locations = []
        for parcel in response.get("@graph", []):
            lat = parcel.get("location", {}).get("lat")
            lon = parcel.get("location", {}).get("long")
            if lat is not None and lon is not None:
                locations.append((lat, lon))
            else:
                # Fallback: Extract first lat, lon from WKT polygon
                wkt = parcel.get("hasGeometry", {}).get("asWKT", "")
                coords = self._parse_wkt(wkt)
                if coords:
                    locations.append(coords)

        return locations

    # Extract first coordinate pair (lat, lon) from WKT POLYGON
    def _parse_wkt(self, wkt: str) -> Optional[Tuple[float, float]]:
        match = re.search(r"POLYGON\(\(\s*([\d\.\-]+) ([\d\.\-]+)", wkt)
        if match:
            lon, lat = float(match.group(1)), float(match.group(2))
            return lat, lon
        return

    # Fetch locations and cache them in memory
    async def fetch_and_cache_locations(self):
        self.app.state.locations = await self.fetch_locations()
        logging.info(f"Cached {len(self.app.state.locations)} locations.")

    # Fetch UAV models the belong to user and cache them in memory
    async def fetch_uavs(self):
        response = await self.get(f'/api/v1/AgriculturalMachines/')
        uavmodels = [ uav.get("model") for uav in response.get("@graph", []) if uav.get("model", None)]
        return uavmodels

    # Fetch UAV models and cache the in memory
    async def fetch_and_cache_uavs(self):
        self.app.state.uavmodels = await self.fetch_uavs()
        logging.info(f"Cached {len(self.app.state.uavmodels)} UAV machines.")

    # Async function to post THI data with JWT authentication
    @backoff.on_exception(backoff.expo, (HTTPException,), max_tries=3)
    async def send_thi(self, lat, lon):

        weather_data = await self.app.weather_app.save_weather_data_thi(lat, lon)
        # Get current unix timestamp
        current_timestamp = int(time.time())
        timezone = weather_data.data['timezone']
        observation = ObservationSchema(
            activityType=self.thi_activity_type,
            title=f"THI: {str(round(weather_data.thi, 2))}",
            details=(
                f"Temperature Humidiy Index on {utils.convert_timestamp_to_string(current_timestamp, timezone)}"
            ),
            phenomenonTime=utils.convert_timestamp_to_string(current_timestamp, timezone, iso=True),
            hasResult=QuantityValueSchema(
                **{
                    "@id": f"urn:farmcalendar:QuantityValue:{uuid4()}",
                    "hasValue": str(round(weather_data.thi, 2))
                }
            ),
            observedProperty="temperature_humidity_index"
        )
        json_payload = observation.model_dump(by_alias=True, exclude_none=True)
        logger.debug(json_payload)
        await self.post('/api/v1/Observations/', json=json_payload)

    # Async function to post Flight Forecast data with JWT authentication
    @backoff.on_exception(backoff.expo, (HTTPException,), max_tries=3)
    async def send_flight_forecast(self, lat, lon, uavmodels):

        fly_statuses = await self.app.weather_app.ensure_forecast_for_uavs_and_location(lat, lon, uavmodels, return_existing=False)
        for fly_status in fly_statuses:
            phenomenon_time = fly_status.timestamp.isoformat()
            weather_str = f"Weather params: {json.dumps(fly_status.weather_params)}"
            observation = ObservationSchema(
                activityType=self.ff_activity_type,
                title=f"{fly_status.uav_model}: {fly_status.status}",
                details=(
                    f"Fligh forecast for {fly_status.uav_model} on "
                    f"lat: {lat}, lon: {lon} at {phenomenon_time}\n\n{weather_str}"
                ),
                phenomenonTime=phenomenon_time,
                madeBySensor=MadeBySensorSchema(name=fly_status.uav_model),
                hasResult=QuantityValueSchema(
                    **{
                        "@id": f"urn:farmcalendar:QuantityValue:{uuid4()}",
                        "hasValue": fly_status.status
                    }
                ),
                observedProperty="flight_forecast_observation"
            )
            json_payload = observation.model_dump(by_alias=True, exclude_none=True)
            logger.debug(json_payload)
            await self.post('/api/v1/Observations/', json=json_payload)

    # Async function to post spray conditions Forecast data with JWT authentication
    @backoff.on_exception(backoff.expo, (HTTPException,), max_tries=3)
    async def send_spray_forecast(self, lat, lon):
        spray_forecasts = await self.app.weather_app.ensure_spray_forecast_for_location(lat, lon, return_existing=False)

        for sf in spray_forecasts:
            phenomenon_time = sf.timestamp.isoformat()

            observation = ObservationSchema(
                activityType=self.sp_activity_type,
                title=f"Spray: {sf.spray_conditions}",
                details=(
                    f"Spray specific conditions on location: "
                    f"lat: {lat}, lon: {lon} at {phenomenon_time}\n\n"
                    f"{json.dumps(sf.detailed_status, indent=2)}"
                ),
                phenomenonTime=phenomenon_time,
                hasResult=QuantityValueSchema(
                    **{
                        "@id": f"urn:farmcalendar:QuantityValue:{uuid4()}",
                        "hasValue": sf.spray_conditions
                    }
                ),
                observedProperty="spray_forecast_observation"
            )

            json_payload = observation.model_dump(by_alias=True, exclude_none=True)
            logger.debug(json_payload)
            await self.post('/api/v1/Observations/', json=json_payload)
