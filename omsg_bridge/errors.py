class APIError(Exception):
    def __init__(self, status, code, message, **details):
        super().__init__(message)
        self.status = status
        self.payload = {"error": {"code": code, "message": message, **details}}
