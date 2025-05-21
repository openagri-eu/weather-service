from datetime import datetime
import logging

from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core import config
from src.core.app import Application

scheduler = AsyncIOScheduler()

class JobManager:
    def __init__(self, scheduler: AsyncIOScheduler, app: Application):
        self.scheduler = scheduler
        self.dynamic_job_ids = set()

    def schedule_farm_job(self, farm, parcels, machines, job_fn):
        job_id = f"forecast_job_{farm['@id'].split(':')[-1]}"
        self.scheduler.add_job(
            job_fn,
            trigger="interval",
            hours=3,
            id=job_id,
            args=[farm, parcels, machines]
        )
        self.dynamic_job_ids.add(job_id)
        logging.info(f"Scheduled forecast job for {farm['name']} as {job_id}")

    def remove_all_dynamic_jobs(self):
        logging.info("Removing all dynamic forecast jobs...")
        for job_id in self.dynamic_job_ids:
            self.scheduler.remove_job(job_id)
            logging.info(f"Removed job {job_id}")
        self.dynamic_job_ids.clear()

    def reschedule_all_farm_jobs(self, farms, get_parcels, get_machines, job_fn):
        self.remove_all_dynamic_jobs()
        logging.info("Rescheduling farm forecast jobs...")
        for farm in farms:
            parcels = get_parcels(farm["@id"])
            machines = get_machines(farm["@id"])
            self.schedule_farm_job(farm, parcels, machines, job_fn)



# Schedule THI tasks for each location
def schedule_tasks(app: FastAPI):
    scheduler.remove_all_jobs()  # Clear old jobs

    if not hasattr(app.state, "locations") or not app.state.locations:
        logging.debug("No locations available for scheduling.")
        return

    for lat, lon in app.state.locations:
        if config.PUSH_THI_TO_FARMCALENDAR:
            scheduler.add_job(
                post_thi_task,
                "interval",
                hours=config.INTERVAL_THI_TO_FARMCALENDAR,
                next_run_time=datetime.now(),
                id=f"thi_task_{lat}_{lon}",
                replace_existing=True,
                args=[app, lat, lon]
            )
            logging.debug("Scheduled THI task for %s, %s", lat, lon)
        if config.PUSH_FLIGHT_FORECAST_TO_FARMCALENDAR:
            scheduler.add_job(
                post_flight_forecast,
                "interval",
                days=5,
                next_run_time=datetime.now(),
                id=f"flight_forecast_task_{lat}_{lon}",
                replace_existing=True,
                args=[app, lat, lon, app.state.uavmodels]
            )
            logging.debug("Scheduled UAV forecast task for %s, %s", lat, lon)
        if config.PUSH_SPRAY_F_TO_FARMCALENDAR:
            scheduler.add_job(
                post_spray_forecast,
                "interval",
                days=5,
                next_run_time=datetime.now(),
                id=f"spray_forecast_task_{lat}_{lon}",
                replace_existing=True,
                args=[app, lat, lon]
            )
            logging.debug("Scheduled spray conditions forecast task for %s, %s", lat, lon)


# Post THI for a single location
async def post_thi_task(app, lat, lon):
    fc_client = app.state.fc_client
    logging.debug(f"Posting THI for {lat}, {lon}")
    await fc_client.send_thi(lat, lon)

# Post flight forecast for a single location
async def post_flight_forecast(app, lat, lon, uavmodels):
    fc_client = app.state.fc_client
    logging.debug(f"Posting Flight forecast for models: {uavmodels} at location: ({lat}, {lon})")
    await fc_client.send_flight_forecast(lat, lon, uavmodels)

# Post spray conditions forecast for a single location
async def post_spray_forecast(app, lat, lon):
    fc_client = app.state.fc_client
    logging.debug(f"Posting spray conditions forecast at location: ({lat}, {lon})")
    await fc_client.send_spray_forecast(lat, lon)


# Fetch locations & update scheduler every 24 hours
async def refresh_locations_and_schedule(app):
    await app.state.fc_client.fetch_and_cache_locations()
    schedule_tasks(app)

# Fetch machines & update scheduler every 24 hours
async def refresh_machines_and_schedule(app):
    await app.state.fc_client.fetch_and_cache_uavs()
    schedule_tasks(app)