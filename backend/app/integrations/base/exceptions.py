class CarrierIntegrationError(RuntimeError):
    pass

class CarrierCredentialsMissing(CarrierIntegrationError):
    pass

class CarrierRemoteError(CarrierIntegrationError):
    def __init__(self, message: str, status_code: int | None = None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload
