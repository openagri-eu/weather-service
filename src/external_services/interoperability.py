import logging
from collections import defaultdict
from typing import List

from src import utils
from src.models.point import Point
from src.models.prediction import Prediction
from src.models.weather_data import WeatherData


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
    def weather_data_to_jsonld(cls, wdata: WeatherData, point: Point) -> dict:
        semantic_data = utils.deepcopy_dict(cls.schema)

        collection_schema = utils.deepcopy_dict(cls.collection_schema)
        collection_schema["@id"] = utils.generate_uuid("weather:data", f"{wdata.data["dt"]}")
        collection_schema["description"] = "Temperature Humidity Index"
        collection_schema["resultTime"] = wdata.data["dt"]
        collection_schema["phenomenonTime"] = wdata.data["dt"]
        collection_schema["hasFeatureOfInterest"]["@id"] = utils.generate_uuid("weather:data:foi", point.id)
        collection_schema["hasFeatureOfInterest"]["@type"].append(point.type)
        collection_schema["hasFeatureOfInterest"]["lat"] = point.location.coordinates[0]
        collection_schema["hasFeatureOfInterest"]["long"] = point.location.coordinates[1]

        item_prefix = "weather:data:thi"
        item_schema = utils.deepcopy_dict(cls.item_schema)
        item_schema["@id"] = utils.generate_uuid(item_prefix, wdata.id)
        item_schema["observedProperty"] = "cf:temperature_humidity_index"
        item_schema["hasResult"] = {
            "@id": utils.generate_uuid(f"{item_prefix}:result", wdata.id),
            "@type": "Result",
            "numericValue": wdata.thi,
            "unit": None
        }

        collection_schema["hasMember"].append(item_schema)
        semantic_data['@graph'].append(collection_schema)
        return semantic_data

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

