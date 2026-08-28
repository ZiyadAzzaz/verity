from fastapi import FastAPI

app = FastAPI()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "diagnostic": "minimal-fastapi-uvicorn"}
