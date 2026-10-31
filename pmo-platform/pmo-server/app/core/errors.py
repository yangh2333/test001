"""统一错误处理与错误码。"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class BizError(Exception):
    """业务异常。"""

    def __init__(self, code: int, message: str, detail: dict = None):
        self.code = code
        self.message = message
        self.detail = detail or {}


# 错误码定义
ERR = {
    "OK": 0,
    "BAD_REQUEST": 40000,
    "UNAUTHORIZED": 40100,
    "FORBIDDEN": 40300,
    "NOT_FOUND": 40400,
    "CONFLICT": 40900,
    "INTERNAL": 50000,
    "VALIDATION": 42200,
}


def ok(data=None, trace_id: str = ""):
    return {"code": 0, "data": data, "trace_id": trace_id}


def register_error_handlers(app: FastAPI):
    @app.exception_handler(BizError)
    async def biz_handler(req: Request, e: BizError):
        return JSONResponse(
            status_code=200,
            content={"code": e.code, "message": e.message, "detail": e.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def val_handler(req: Request, e: RequestValidationError):
        return JSONResponse(
            status_code=200,
            content={"code": ERR["VALIDATION"], "message": "参数校验失败", "detail": e.errors()},
        )

    @app.exception_handler(Exception)
    async def exc_handler(req: Request, e: Exception):
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=200,
            content={"code": ERR["INTERNAL"], "message": str(e)},
        )
