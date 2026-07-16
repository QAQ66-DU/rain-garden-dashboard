from enum import StrEnum


class LocationDisclosure(StrEnum):
    WITHHELD = "withheld"
    APPROXIMATE = "approximate"
    PRIVATE = "private"


class DeviceType(StrEnum):
    WEATHER_STATION = "weather_station"
    SOIL_MOISTURE_SENSOR = "soil_moisture_sensor"
    WATER_LEVEL_SENSOR = "water_level_sensor"


class OperationalOverride(StrEnum):
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


class IngestionStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class QualityFlag(StrEnum):
    VALID = "valid"
    OUT_OF_RANGE = "out_of_range"
    SUSPECT = "suspect"
