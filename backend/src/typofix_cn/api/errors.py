from fastapi import HTTPException


def invalid_input(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": "INVALID_INPUT", "message": message})
