class AppException(Exception):
    def __init__(self, detail: str, status_code: int = 500):
        self.detail = detail
        self.status_code = status_code


class NotFoundException(AppException):
    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(detail, 404)


class ConflictException(AppException):
    def __init__(self, detail: str = "Conflicto"):
        super().__init__(detail, 409)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "No autorizado"):
        super().__init__(detail, 401)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Acceso denegado"):
        super().__init__(detail, 403)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Solicitud incorrecta"):
        super().__init__(detail, 400)


class ValidationException(AppException):
    def __init__(self, detail: str = "Error de validación"):
        super().__init__(detail, 400)
