from fastapi import FastAPI, Request
import asyncio
from uvicorn import Config, Server
from processor import processImage


# 각각의 FastAPI 애플리케이션 정의
app1 = FastAPI()
app2 = FastAPI()
app3 = FastAPI()
app4 = FastAPI()
app5 = FastAPI()


# 이미지 처리 함수 정의
def process_image_data(image_data):
    processed_image = processImage(image_data)
    return processed_image


# 서버 1 | port 8000 라우트 정의
@app1.post("/process")
async def process_task_app1(request: Request):
    image = await request.body()
    processed_image_hex = process_image_data(image)
    return {"processed_image": processed_image_hex}


# 서버 2 | port 8001 라우트 정의
@app2.post("/process")
async def process_task_app2(request: Request):
    image = await request.body()
    processed_image_hex = process_image_data(image)
    return {"processed_image": processed_image_hex}


# 서버 3 | port 8002 라우트 정의
@app3.post("/process")
async def process_task_app3(request: Request):
    image = await request.body()
    processed_image_hex = process_image_data(image)
    return {"processed_image": processed_image_hex}


# 서버 4 | port 8003 라우트 정의
@app4.post("/process")
async def process_task_app3(request: Request):
    image = await request.body()
    processed_image_hex = process_image_data(image)
    return {"processed_image": processed_image_hex}


# 서버 5 | port 8004 라우트 정의
@app5.post("/process")
async def process_task_app3(request: Request):
    image = await request.body()
    processed_image_hex = process_image_data(image)
    return {"processed_image": processed_image_hex}


# 각 FastAPI 애플리케이션을 uvicorn 서버로 실행하는 함수
async def run_server(app, port):
    config = Config(app=app, host="localhost", port=port)
    server = Server(config)
    await server.serve()


# asyncio 루프 실행
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    tasks = [
        loop.create_task(run_server(app1, 8000)),
        loop.create_task(run_server(app2, 8001)),
        loop.create_task(run_server(app3, 8002)),
        loop.create_task(run_server(app4, 8003)),
        loop.create_task(run_server(app5, 8004)),
    ]
    loop.run_until_complete(asyncio.wait(tasks))