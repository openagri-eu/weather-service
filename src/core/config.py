import os
import dotenv


dotenv.load_dotenv()

# LOGGING
LOGGING_LEVEL = os.environ.get('LOGGING_LEVEL', 'INFO')

# APP
WEATHER_SRV_PORT = os.environ.get('WEATHER_SRV_PORT', '8000')
WEATHER_SRV_HOSTNAME = os.environ.get('WEATHER_SRV_HOSTNAME', 'weathersrv')

# DB
DATABASE_URI = os.environ.get('DATABASE_URI', 'mongodb://root:root@localhost:27017/')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'openagridb')
OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')

# ALLOWED_HOSTS
EXTRA_ALLOWED_HOSTS = os.environ.get('EXTRA_ALLOWED_HOSTS', "*").replace(' ', '').split(',')

# GATEKEEPER
GATEKEEPER_URL= os.environ.get('GATEKEEPER_URL', '')
GATEKEEPER_APP_PORT = os.environ.get('GATEKEEPER_APP_PORT', '8001')
GATEKEEPER_USERNAME = os.environ.get('GATEKEEPER_SUPERUSER_USERNAME', '')
GATEKEEPER_PASSWORD = os.environ.get('GATEKEEPER_SUPERUSER_PASSWORD', '')

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', ''))
KEY = os.environ.get('JWT_KEY', '')
ALGORITHM = os.environ.get('ALGORITHM', '')
CRYPT_CONTEXT_SCHEME = os.environ.get('CRYPT_CONTEXT_SCHEME', '')
