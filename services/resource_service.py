from fastapi import FastAPI, Request

app = FastAPI(title="Protected Resource Service")

@app.get("/health")
def health():
    return {"service": "resource", "status": "ok"}

@app.api_route("/api/data", methods=["GET", "POST"])
async def data(request: Request):
    return {
        "service": "resource",
        "resource": "data",
        "message": "Protected business data response",
        "method": request.method,
    }

@app.api_route("/api/admin", methods=["GET", "POST"])
async def admin(request: Request):
    return {
        "service": "resource",
        "resource": "admin",
        "message": "Protected administrative response",
        "method": request.method,
    }
