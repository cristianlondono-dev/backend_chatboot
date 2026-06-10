class NotFoundException(Exception):
    def __init__(self, entity: str, identifier: str = ""):
        self.entity = entity
        self.identifier = identifier
        msg = f"{entity} no encontrado"
        if identifier:
            msg += f" (id: {identifier})"
        super().__init__(msg)


class ConflictException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class UnprocessableException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
