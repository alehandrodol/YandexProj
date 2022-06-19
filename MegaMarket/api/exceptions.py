class InvalidImport(Exception):
    """Невалидная схема документа или входные данные не верны."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class InvalidUUID(Exception):
    """Невалидная запись ID"""
    def __init__(self):
        self.message = "Invalid uuid format"

    def __str__(self):
        return self.message


class InvalidDateFormat(Exception):
    """Невалидная запись времени"""

    def __init__(self):
        self.message = "Invalid date format, date should be in ISO 8601 stamp"

    def __str__(self):
        return self.message
