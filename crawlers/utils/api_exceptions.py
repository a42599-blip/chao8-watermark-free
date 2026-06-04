class APIError(Exception):
    pass
class APIConnectionError(APIError):
    pass
class APIResponseError(APIError):
    pass
class APIUnavailableError(APIError):
    pass
class APIUnauthorizedError(APIError):
    pass
class APINotFoundError(APIError):
    pass
