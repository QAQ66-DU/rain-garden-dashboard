from enum import StrEnum


class LocationDisclosure(StrEnum):
    WITHHELD = "withheld"
    APPROXIMATE = "approximate"
    PRIVATE = "private"


class DeviceType(StrEnum):
    WEATHER_STATION = "weather_station"
    SOIL_MOISTURE_SENSOR = "soil_moisture_sensor"
    WATER_LEVEL_SENSOR = "water_level_sensor"
    MULTI_DEPTH_SOIL_PROBE = "multi_depth_soil_probe"


class MonitoringFeatureType(StrEnum):
    SWALE = "swale"
    TREE_PIT = "tree_pit"


class SensorConfigurationStatus(StrEnum):
    CONFIGURED = "configured"
    PENDING = "pending"


class UnitConfirmationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SYNTHETIC_DEMO_ONLY = "synthetic_demo_only"


class MetricGroup(StrEnum):
    HYDROLOGY = "hydrology"
    SOIL = "soil"
    WEATHER = "weather"
    OPERATIONAL = "operational"


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
