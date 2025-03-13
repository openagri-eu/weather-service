import logging

from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core import config

scheduler = AsyncIOScheduler()


# Schedule THI tasks for each location
def schedule_tasks(app: FastAPI):
    scheduler.remove_all_jobs()  # Clear old jobs

    if not hasattr(app.state, "locations") or not app.state.locations:
        logging.debug("No locations available for scheduling.")
        return

    for lat, lon in app.state.locations:
        scheduler.add_job(
            post_thi_task,
            "interval",
            hours=config.INTERVAL_THI_TO_FARMCALENDAR,
            id=f"thi_task_{lat}_{lon}",
            replace_existing=True,
            args=[app, lat, lon]
        )
        logging.debug(f"Scheduled THI task for {lat}, {lon}")
        scheduler.add_job(
            post_flight_forecast,
            "interval",
            days=5,
            id=f"flight_forecast_task_{lat}_{lon}",
            replace_existing=True,
            args=[app, lat, lon, app.state.uavmodels]
        )

# Post THI for a single location
async def post_thi_task(app, lat, lon):
    fc_client = app.state.fc_client
    logging.debug(f"Posting THI for {lat}, {lon}")
    await fc_client.send_thi(lat, lon)

# Post flight forecast for a single location
async def post_flight_forecast(app, lat, lon, uavmodels):
    fc_client = app.state.fc_client
    logging.debug(f"Posting Flight Forecast for models: {uavmodels} at location: ({lat}, {lon})")
    await fc_client.send_flight_forecast(lat, lon, uavmodels)


# Fetch locations & update scheduler every 24 hours
async def refresh_locations_and_schedule(app):
    await app.state.fc_client.fetch_and_cache_locations()
    schedule_tasks(app)


def start_scheduler(app: FastAPI):

    schedule_tasks(app)

    # Refresh locations and reschedule every 24 hours
    scheduler.add_job(refresh_locations_and_schedule, "interval", hours=24, args=[app])

    scheduler.start()
