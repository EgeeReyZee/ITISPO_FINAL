import httpx
import os
import logging
from fastapi import FastAPI, Request, Response, HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOTIFICATIONS_SVC = os.getenv("NOTIFICATIONS_SVC_URL", "http://notifications-svc-s09:8131")

app = FastAPI(title="API Gateway", version="1.0.0")


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    url = f"{NOTIFICATIONS_SVC}/{path}"
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    logger.info(f"Proxying {request.method} /api/{path} -> {url}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                params=request.query_params,
            )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Upstream service unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream service timeout")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}