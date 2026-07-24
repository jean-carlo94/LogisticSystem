from enum import Enum


class ActionType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    STATUS_CHANGED = "STATUS_CHANGED"
