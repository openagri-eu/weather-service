import base64
import functools
import glob
from importlib import import_module
import inspect
import logging
import os
import struct
import copy
import uuid

import httpx


logger = logging.getLogger(__name__)


def deepcopy_dict(d: dict) -> dict:
    return copy.deepcopy(d)


def extract_value_from_dict_path(d: dict, path: list):
    return functools.reduce(
                lambda elem, current_path: elem[current_path] if elem and current_path in elem else None,
                path,
                d
            )


# Function to generate a UUID with a specific prefix
def generate_uuid(prefix, identifier=None):
    return f"urn:openagri:{prefix}:{identifier if identifier else uuid.uuid4()}"

async def http_get(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


## Temperature Humidity Index
# https://www.pericoli.com/en/temperature-humidity-index-what-you-need-to-know-about-it/

def calculate_thi(temperature: float, relative_humidity: float) -> float:
    relative_humidity = relative_humidity / 100 # Convert to % percentage
    thi = (0.8 * temperature) + (relative_humidity * (temperature - 14.4)) + 46.4
    return round(thi, 2)


def number_to_base32_string(num: float) -> str:
    '''
    Explanation:

    Struct Packing: struct.pack('>q', num) converts the integer number to a byte array in big-endian format using the >q format (signed long long, 8 bytes).
    Base32 Encoding: base64.b32encode encodes the byte array to a base-32 encoded bytes object.
    Decoding: .decode('utf-8') converts the bytes object to a string.
    Stripping Equals: .rstrip('=') removes any trailing equal signs used for padding in base-32 encoding.
    '''
    # Convert the number to a byte array
    byte_array = struct.pack('>q', num)  # Use '>q' for long long (8 bytes)
    
    # Encode the byte array using base32
    base32_encoded = base64.b32encode(byte_array).decode('utf-8').rstrip('=')
    
    return base32_encoded


def load_classes(pathname, base_classes):
    classes = []
    for path in glob.glob(pathname, recursive=True):
        module = import_module(os.path.splitext(path)[0].strip('./').replace('/', '.'))
        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and obj not in base_classes and issubclass(obj, base_classes):
                classes.append(obj)

    return classes
