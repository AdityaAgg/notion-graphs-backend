import enum


class XAxisType(enum.Enum):
    NOT_TIME = 1,
    TIMESTAMP = 2,
    DATETIME_DATE = 3,
    DATE = 4
