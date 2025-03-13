import re
from typing import Optional, Tuple
from fastapi import FastAPI, HTTPException
import logging

import backoff

from src.core import config
from src import utils
from src.services.base import MicroserviceClient

class FarmCalendarServiceClient(MicroserviceClient):

    def __init__(self, app: FastAPI):
        super().__init__(base_url=config.FARM_CALENDAR_URL, service_name="Farm Calendar", app=app)

    # Create THI Observation Activity Type
    async def fetch_or_create_thi_activity_type(self) -> str:
        activity_type = 'THI_Observation'
        act_jsonld = await self.get(f'/api/v1/FarmCalendarActivityTypes/?name={activity_type}')

        if not self._get_activity_type_id(act_jsonld):
            json_payload = {
                "name": f"{activity_type}",
                "description": "Activity type collecting observed values for Temperature Humidity Index",
            }
            act_jsonld = await self.post('/api/v1/FarmCalendarActivityTypes/', json=json_payload)

        self.thi_activity_type = self._get_activity_type_id(act_jsonld)

    # Create Flight Forecast Observation Activity Type
    async def fetch_or_create_flight_forecast_activity_type(self) -> str:
        raise NotImplementedError

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
        raise NotImplementedError

    # Async function to post THI data with JWT authentication
    @backoff.on_exception(backoff.expo, (HTTPException,), max_tries=3)
    async def send_thi(self, lat, lon):

        weather_data = await self.app.weather_app.get_thi(lat, lon)
        unix_timestamp = weather_data.data['dt']
        timezone = weather_data.data['timezone']

        json_payload = {
            "activityType": self.thi_activity_type,
            "title": "THI",
            "details": f"Temperature Humidiy Index on {utils.convert_timestamp_to_string(unix_timestamp, timezone)}",
            "phenomenonTime": utils.convert_timestamp_to_string(unix_timestamp, timezone, iso=True),
            "hasResult": {
                "@id": "urn:farmcalendar:QuantityValue:37b4cbab-1fa1-56c7-b72e-44464d52c21e",
                "@type": "QuantityValue",
                "unit": "null",
                "numericValue": str(round(weather_data.thi, 2))
            },
            "observedProperty": "temperature_humidity_index"
        }

        await self.post('/api/v1/Observations/', json=json_payload)

    # Async function to post Flight Forecast data with JWT authentication
    @backoff.on_exception(backoff.expo, (HTTPException,), max_tries=3)
    async def send_flight_forecast(self, lat, lon, uavmodels):
        raise NotImplementedError

