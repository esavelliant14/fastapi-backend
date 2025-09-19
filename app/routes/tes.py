# routes/bod.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/receive")
async def receive_data(request: Request):
    data = await request.json()  # dict kiriman dari Laravel
    ip = data.get("ip")
    interface = data.get("interface")

    print(f"Data diterima dari Laravel: ip={ip}, interface={interface}")

    return JSONResponse({
        "status": "ok",
        "message": "Data diterima",
        "ip": ip,
        "interface": interface
    })

