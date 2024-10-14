import logging
from typing import List
from collections import defaultdict

from src import utils
from src.models.point import Point
from src.models.prediction import Prediction


logger = logging.getLogger(__name__)

# TODO: Re-Implement this class using OCSM
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
        '@type': ["ObservationCollection","WeatherForecast"],
        "description": "5-day weather forecast on 2024-10-01T12:00:00+00:00",
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

    property_schema = { # TODO add these to data_specifications objects on defaults.json
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
    def predictions_to_jsonld(cls, predictions: List[Prediction], spatial_entity: Point) -> dict:
        property_schema = cls.property_schema
        semantic_data = utils.deepcopy_dict(cls.schema)

        tmpst_buckets = defaultdict(list)
        for pred in predictions:
            tmpst_buckets[pred.timestamp].append(pred)

        try:
            for timestamp, preds in tmpst_buckets.items():
                collection_schema = utils.deepcopy_dict(cls.collection_schema)
                collection_schema["@id"] = utils.generate_uuid("weather:forecast")
                collection_schema["resultTime"] = timestamp
                collection_schema["phenomenonTime"] = timestamp
                collection_schema["hasFeatureOfInterest"]["@id"] = utils.generate_uuid("weather:forecast:foi")
                collection_schema["hasFeatureOfInterest"]["@type"].append(spatial_entity.type)
                collection_schema["hasFeatureOfInterest"]["lat"] = spatial_entity.location.coordinates[0]
                collection_schema["hasFeatureOfInterest"]["long"] = spatial_entity.location.coordinates[1]

                for p in preds:
                    item_prefix = f"weather:forecast:{property_schema[p.measurement_type]["measurement"].lower()}"
                    item_schema = utils.deepcopy_dict(cls.item_schema)
                    item_schema["@id"] = utils.generate_uuid(item_prefix)
                    item_schema["observedProperty"] = f"cf:{p.measurement_type}"
                    item_schema["hasResult"] = {
                        "@id": utils.generate_uuid(f"{item_prefix}:result"),
                        "@type": "Result",
                        "numericValue": p.value,
                        "unit": property_schema[p.measurement_type]["unit"]
                    }

                collection_schema["hasMember"].append(item_schema)
                semantic_data['@graph'].append(collection_schema)
        except Exception as e:
            logger.exception(e)
        else:
            return semantic_data
