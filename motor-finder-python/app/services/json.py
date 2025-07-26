from fastapi.responses import JSONResponse
from fastapi import status

def return_json(message: str = "Success", data: dict = None, code: int = status.HTTP_200_OK):
    return JSONResponse(
        status_code=code,
        content={"message": message, "data": data}
    )

def return_error_json(message: str = "Error", data: dict = None, code: int = status.HTTP_400_BAD_REQUEST):
    return JSONResponse(
        status_code=code,
        content={"message": message, "data": data}
    )