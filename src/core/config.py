import os
import dotenv


dotenv.load_dotenv()

# LOGGING
LOGGING_LEVEL = os.environ.get('LOGGING_LEVEL', 'INFO')

# DB
DATABASE_URI = os.environ.get('DATABASE_URI', 'mongodb://root:root@localhost:27017/')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'openagridb')
OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')

ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
KEY: str = "c2bab29d257f0ffc52d9ac677d4ff6d1d9d5e92e3d3939d3f4cwc"
