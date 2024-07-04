from fastapi import FastAPI, Request
import asyncio
from uvicorn import Config, Server
from multiprocessing import Process
from processor import processImage


# 이미지 처리 함수 정의
def processImageData(image_data):
    processed_image = processImage(image_data)
    return processed_image


# 서버 애플리케이션을 생성하는 함수
def createApp():
    app = FastAPI()

    @app.post("/process")
    async def processTask(request: Request):
        image = await request.body()
        print(f'worker.py_image data: {image}')
        processed_image_hex = processImageData(image)
        return {"processed_image": processed_image_hex}
    
    @app.get("/status")
    async def status():
        return {"status": "Server is running"}

    return app


# 각 FastAPI 애플리케이션을 uvicorn 서버로 실행하는 함수
def runServer(port):
    app = createApp()
    config = Config(app=app, host="localhost", port=port)
    server = Server(config)
    asyncio.run(server.serve())


# 멀티프로세스를 사용하여 서버 실행
if __name__ == "__main__":
    # ports = [8000, 8001, 8002, 8003, 8004]
    ports = [8000, 8001]
    processes = [Process(target=runServer, args=(port,)) for port in ports]

    for process in processes:
        process.start()

    for process in processes:
        process.join()