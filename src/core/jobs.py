import logging
import json
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.interoperability import MadeBySensorSchema, ObservationSchema, QuantityValueSchema
from utils import extract_coordinates_from_parcel
from services.farmcalendar_service import FarmCalendarServiceClient


logger = logging.getLogger(__name__)


async def run_forecast_for_farm(farm: dict, parcels: list, machines: list, fc_client: FarmCalendarServiceClient):
    farm_name = farm.get("name", "Unknown")
    farm_id = farm.get("@id")
    logger.debug(f"🌾 Running forecast for farm '{farm_name}' with {len(parcels)} parcels and {len(machines)} machines.")

    for parcel in parcels:
        coords = extract_coordinates_from_parcel(parcel)
        if not coords:
            logger.debug(f"⚠️ Skipping parcel with missing geometry")
            continue
        lat, lon = coords

        uavmodels = [m for m in machines]
        for machine in machines:
            machine_forecasts.append({
                "machine_id": machine["@id"],
                "name": machine["name"],
            })

        fly_statuses = await fc_client.app.weather_app.ensure_forecast_for_uavs_and_location(lat, lon, uavmodels, return_existing=False)
        for fly_status in fly_statuses:
            phenomenon_time = fly_status.timestamp.isoformat()
            weather_str = f"Weather params: {json.dumps(fly_status.weather_params)}"
            observation = ObservationSchema(
                activityType=fc_client.ff_activity_type,
                title=f"{fly_status.uav_model}: {fly_status.status}",
                details=(
                    f"Fligh forecast for {fly_status.uav_model} @ {farm_name}"
                    f"Valid from {phenomenon_time} and for the next 3 hours\n\n{weather_str}"
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
            try:
                await fc_client.post_observation('/api/v1/Observations/', json=json_payload)
                logger.debug(f"✅ Posted forecast observation for {fly_status.uav_model} @ {farm_name}")
            except Exception as e:
                logger.debug(f"❌ Error posting observation: {e}")

