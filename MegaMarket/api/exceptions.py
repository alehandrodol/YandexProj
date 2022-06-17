class InvalidImport(Exception):
    """Невалидная схема документа или входные данные не верны."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
