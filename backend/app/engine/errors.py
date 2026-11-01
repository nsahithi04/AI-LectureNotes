"""The one error type the engine raises. The code says what went wrong, and the message is safe to show users."""


class EngineError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
