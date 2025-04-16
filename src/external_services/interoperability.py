import logging
from collections import defaultdict
from typing import List

from src import utils
from src.models.point import Point
from src.models.prediction import Prediction
from src.models.spray import SprayForecast
from src.models.uav import FlyStatus
from src.models.weather_data import WeatherData
from src.ocsm.base import FeatureOfInterest, JSONLDGraph
from src.ocsm.spray import SprayForecastDetailedStatus, SprayForecastObservation, SprayForecastResult
from src.ocsm.uav import FlightConditionObservation, FlightConditionResult
from src.ocsm.weather_data import THIObservation, THIResult


logger = logging.getLogger(__name__)


class InteroperabilitySchema:

    context_schema = [
              "https://w3id.org/ocsm/main-context.jsonld",
              {
                  "qudt": "http://qudt.org/vocab/unit/",
                  "cf" : "https://vocab.nerc.ac.uk/standard_name/"
              }
          ]

    graph_schema = []

    item_schema = {
            "@id": "urn:openagri:weather:forecast:temp:72d9fb43-53f8-4ec8-a33c-fa931360259a",
            "@type": "Observation",
            "observedProperty": "cf:air_temperature",
            "hasResult": {
                "@id": "",
                "@type": "Result",
                "numericValue": 22.53,
                "unit": "qudt:DEG_C"
            }
        }

    collection_schema = {
        '@id': "",
        '@type': ["ObservationCollection"],
        "description": "",
        "hasFeatureOfInterest": {
            "@id": "",
            "@type": ["FeatureOfInterest"],
            "long" : 39.1436719643054,
            "lat": 27.40518186700786
        },
        "source": "openweathermaps",
        "resultTime": "2024-10-01T12:00:00+00:00",
        "phenomenonTime": "2024-10-01T12:00:00+00:00",
        "hasMember": []
    }

    schema = {
        '@context': context_schema,
        '@graph': []
    }

    property_schema = {
        'ambient_temperature': {
          'measurement': 'Temperature',
          'unit': 'qudt:DEG_C',
        },
        'ambient_humidity': {
          'measurement': 'RelativeHumidity',
          'unit': 'Percent',
        },
        'wind_speed': {
          'measurement': 'WindSpeed',
          'unit': 'MeterPerSecond',
        },
        'wind_direction': {
          'measurement': 'WindDirection',
          'unit': 'Degree',
        },
        'precipitation': {
          'measurement': 'Precipitation',
          'unit': 'Millimetre',
        },
    }

    @classmethod
    def weather_data_to_jsonld(cls, wdata: WeatherData) -> JSONLDGraph:

        graph = [
            FeatureOfInterest(
                        **{
                            "@id": utils.generate_urn('Location', obj_id=wdata.spatial_entity.location.id),
                            "lon": wdata.spatial_entity.location.coordinates[1],
                            "lat": wdata.spatial_entity.location.coordinates[0]
                        }
                    ).model_dump()
        ]
        graph.append(THIObservation(
            **{
                "@id": utils.generate_uuid("weather:data:thi", wdata.id),
                "description": "Temperature Humidity Index",
                "hasFeatureOfInterest": utils.generate_urn('Location', obj_id=wdata.spatial_entity.location.id),
                "weatherSource": "openweathermaps",
                "resultTime": wdata.data["dt"],
                "phenomenonTime": wdata.data["dt"],
                "hasResult": THIResult(
                    **{
                        "@id": utils.generate_urn("weather:data:thi", 'result', obj_id=wdata.id),
                        "@type": ["Result", "THI"],
                        "hasValue": wdata.thi
                    }
                )
            }
        ).model_dump(exclude_none=True))
        jsonld = JSONLDGraph(
                    **{
                        "@context": [
                            "https://w3id.org/ocsm/main-context.jsonld",
                            {
                                "qudt": "http://qudt.org/vocab/unit/",
                                "cf": "https://vocab.nerc.ac.uk/standard_name/"
                            }
                        ],
                        "@graph": graph
                    }
                )
        return jsonld

    @classmethod
    def predictions_to_jsonld(cls, predictions: List[Prediction], spatial_entity: Point) -> dict:
        property_schema = cls.property_schema
        semantic_data = utils.deepcopy_dict(cls.schema)

        tmpst_buckets = defaultdict(list)
        for pred in predictions:
            tmpst_buckets[pred.timestamp].append(pred)

        try:
            for timestamp, preds in tmpst_buckets.items():
                collection_schema = utils.deepcopy_dict(cls.collection_schema)
                collection_schema["@id"] = utils.generate_uuid("weather:forecast", f"{timestamp}")
                collection_schema["@type"].append("WeatherForecast")
                collection_schema["description"] = "5-day weather forecast"
                collection_schema["resultTime"] = timestamp
                collection_schema["phenomenonTime"] = timestamp
                collection_schema["hasFeatureOfInterest"]["@id"] = utils.generate_uuid("weather:forecast:foi", spatial_entity.id)
                collection_schema["hasFeatureOfInterest"]["@type"].append(spatial_entity.type)
                collection_schema["hasFeatureOfInterest"]["lat"] = spatial_entity.location.coordinates[0]
                collection_schema["hasFeatureOfInterest"]["long"] = spatial_entity.location.coordinates[1]

                for p in preds:
                    item_prefix = f"weather:forecast:{property_schema[p.measurement_type]["measurement"].lower()}"
                    item_schema = utils.deepcopy_dict(cls.item_schema)
                    item_schema["@id"] = utils.generate_uuid(item_prefix, p.id)
                    item_schema["observedProperty"] = f"cf:{p.measurement_type}"
                    item_schema["hasResult"] = {
                        "@id": utils.generate_uuid(f"{item_prefix}:result", p.id),
                        "@type": "Result",
                        "numericValue": p.value,
                        "unit": property_schema[p.measurement_type]["unit"]
                    }

                collection_schema["hasMember"].append(item_schema)
                semantic_data['@graph'].append(collection_schema)
        except Exception as e: # pylint: disable=W0718:broad-exception-caught
            logger.exception(e)
        else:
            return semantic_data

    @classmethod
    def serialize_flystatus(cls, statuses: List[FlyStatus]) -> JSONLDGraph:
        first = statuses[0]
        graph = [
                    FeatureOfInterest(
                                **{
                                    "@id": utils.generate_urn('Location', obj_id=first.location.id),
                                    "lon": first.location.coordinates[1],
                                    "lat": first.location.coordinates[0]
                                }
                            ).model_dump()
                ]
        for fs in statuses:
            graph.append(FlightConditionObservation(
                **{
                                "@id": utils.generate_urn(FlyStatus.__name__, obj_id=fs.id),
                                "description": f"Flight conditions for a {fs.uav_model} drone model on 2025-03-05T18:00:00",
                                "hasFeatureOfInterest": utils.generate_urn('Location', obj_id=fs.location.id),
                                "madeBySensor": utils.generate_urn(FlyStatus.__name__, 'model', obj_id=fs.uav_model),
                                "weatherSource": "openweathermaps",
                                "resultTime": fs.timestamp,
                                "phenomenonTime": fs.timestamp,
                                "hasResult": FlightConditionResult(
                                    **{
                                        "@id": utils.generate_urn(FlyStatus.__name__, 'result', obj_id=fs.id),
                                        "@type": ["Result", "FlightConditionStatus"],
                                        "status": fs.status,
                                        "temperature": fs.weather_params["temp"],
                                        "precipitation": fs.weather_params["precipitation"],
                                        "windSpeed": fs.weather_params["wind"]
                                    }
                                )
                            }
            ).model_dump(exclude_none=True))
        jsonld = JSONLDGraph(
                    **{
                        "@context": [
                            "https://w3id.org/ocsm/main-context.jsonld",
                            {
                                "qudt": "http://qudt.org/vocab/unit/",
                                "cf": "https://vocab.nerc.ac.uk/standard_name/"
                            }
                        ],
                        "@graph": graph
                    }
        )
        return jsonld

    @classmethod
    def serialize_spray_forecasts(cls, forecasts: List[SprayForecast]) -> JSONLDGraph:
        first = forecasts[0]
        graph = [
            FeatureOfInterest(
                **{
                    "@id": utils.generate_urn('Location', obj_id=first.location.id),
                    "lon": first.location.coordinates[1],
                    "lat": first.location.coordinates[0]
                }
            ).model_dump()
        ]

        for sf in forecasts:
            graph.append(SprayForecastObservation(
                **{
                    "@id": utils.generate_urn(SprayForecast.__name__, obj_id=sf.id),
                    "description": f"Spray Forecast on {sf.timestamp}",
                    "hasFeatureOfInterest": utils.generate_urn('Location', obj_id=sf.location.id),
                    "weatherSource": sf.source,
                    "resultTime": sf.timestamp,
                    "phenomenonTime": sf.timestamp,
                    "hasResult": SprayForecastResult(
                        **{
                            "@id": utils.generate_urn(SprayForecast.__name__, 'result', obj_id=sf.id),
                            "@type": ["Result", "SprayForecastResult"],
                            "spray_conditions": sf.spray_conditions,
                        }
                    ),
                    "sprayForecastDetailedStatus": SprayForecastDetailedStatus(
                        **{
                            "@id": utils.generate_urn(SprayForecast.__name__, 'result', obj_id=sf.id),
                            "@type": ["sprayForecastDetailedStatus"],
                            "temperatureStatus": sf.detailed_status["temperature_status"],
                            "windStatus": sf.detailed_status["wind_status"],
                            "precipitationStatus": sf.detailed_status["precipitation_status"],
                            "humidityStatus": sf.detailed_status["humidity_status"],
                            "deltaTStatus": sf.detailed_status["delta_t_status"],
                        }
                    )
                }
            ).model_dump(exclude_none=True))

        return JSONLDGraph(
            **{
                "@context": [
                    "https://w3id.org/ocsm/main-context.jsonld",
                    {
                        "qudt": "http://qudt.org/vocab/unit/",
                        "cf": "https://vocab.nerc.ac.uk/standard_name/"
                    }
                ],
                "@graph": graph
            }
        )