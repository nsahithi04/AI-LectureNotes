"""The error type the meetings layer raises. The API turns the code into an HTTP status."""


class MeetingError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
