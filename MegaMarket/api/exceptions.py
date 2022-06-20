from enum import Enum, unique


@unique
class IdExceptionsTypes(Enum):
    uuid = "uuid"
    not_found = "not found"


class InvalidImport(ValueError):
    """Невалидная схема документа или входные данные не верны."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ElementIdException(ValueError):
    """Невалидная запись ID"""
    def __init__(self, exception_type: IdExceptionsTypes):
        self.type = exception_type
        if exception_type == IdExceptionsTypes.uuid:
            self.message = "Invalid uuid format"
        elif exception_type == IdExceptionsTypes.not_found:
            self.message = "Element with given ID is not found"

    def __str__(self):
        return self.message


class InvalidDateFormat(ValueError):
    """Невалидная запись времени"""

    def __init__(self):
        self.message = "Invalid date format, date should be in ISO 8601 stamp"

    def __str__(self):
        return self.message
