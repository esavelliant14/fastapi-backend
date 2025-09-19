from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/receive")
async def receive_data(request: Request):
    # ambil data yang dikirim Laravel
    data = await request.json()  # hasil dict
    ip = data.get("ip")
    interface = data.get("interface")

    print(f"Data diterima dari Laravel: ip={ip}, interface={interface}")

    # balikan response ke Laravel
    return JSONResponse({
        "status": "ok",
        "message": "Data diterima",
        "ip": ip,
        "interface": interface
    })

