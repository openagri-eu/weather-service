class UAVModelNotFoundError(Exception):
    def __init__(self, uav_model: str):
        self.message = f"UAV model '{uav_model}' not found"
        super().__init__(self.message)


class InvalidWeatherDataError(Exception):
    def __init__(self):
        self.message = "Invalid weather data received from OpenWeatherMap"
        super().__init__(self.message)


class RefreshJWTTokenError(Exception):
    def __init__(self, service_name):
        self.message = f"Authentication failed for {service_name} service. JWT token may be expired."
        super().__init__(self.message)
