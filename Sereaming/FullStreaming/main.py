import ray
import httpx
from quart import Quart, websocket
import asyncio
import multiprocessing
import uvicorn

app = Quart(__name__)

# Ray 초기화
ray.init(ignore_reinit_error=True)


# 작업자 풀 생성
worker_pool = [8000, 8001, 8002, 8003, 8004]


@ray.remote
class WorkerStatus:
    def __init__(self, worker_pool):
        self.status = {port: True for port in worker_pool}
        
    def getAvailableWorker(self):
            # 작업 가능한 작업자가 있을 때     
            if True in self.status.values():
                for port, available in self.status.items():
                    if available:
                        self.status[port] = False  # 작업을 할당할 때 바로 상태를 업데이트
                        return port
            # 작업 가능자가 없을 때
            else:
                return None
        
    def upDateStatus(self, port, status):
        self.status[port] = status
        
@ray.remote
class TaskQueue:
    def __init__(self):
        self.queue = []

    def put(self, item):
        self.queue.append(item)
        
    def view(self, ):
        print(f"queue check: {self.queue}")

    def get(self):
        if len(self.queue) > 0:
            return self.queue.pop(0)
        else:
            return None


# WorkerStatus와 TaskQueue Actor 인스턴스 생성
worker_status = WorkerStatus.remote(worker_pool)
task_queue = TaskQueue.remote()


@app.websocket("/upload")
async def upload() :
    while True:
        data = await websocket.receive_json()
        image_bytes = bytes.fromhex(data["image"])
        
        # Ray의 TaskQueue Actor에 데이터를 넣습니다.
        await task_queue.put.remote(image_bytes)


def taskProcessor():
    while True:
        try:
            task = task_queue.get.remote()
            
            # 작업을 할당
            available_worker_port = worker_status.getAvailableWorker.remote()  # 가용한 worker_port 가져오기
            if available_worker_port == None: # 작업 가능자가 없을 때
                print("작업자가 없습니다.")
            else:
                handleImageProcessing.remote(task, available_worker_port)
        except:
            pass # 스택이 없을 때
                
@ray.remote
def handleImageProcessing(image_bytes, port):
    result = processOnWorker.remote(image_bytes, port)
    if result:
        asyncio.run(websocket.send_json({"status": "processing", "processed_image": result}))
    else:
        asyncio.run(websocket.send_json({"status": "error", "message": "Processing failed"}))
    ray.get(worker_status.updateStatus.remote(port, True))
        
        
@ray.remote
def processOnWorker(image_data, port):
    url = f"http://127.0.0.1:{port}/process"
    headers = {"Content-Type": "application/octet-stream"}
    with httpx.Client() as client:
        try:
            response = client.post(url, content=image_data, headers=headers, timeout=2.5)
            if response.status_code == 200:
                result = response.json()["processed_image"]
                print(f"Processed image on port {port}: {result}")
                return result
            else:
                print(f"Failed to process image on port {port}: {response.status_code}")
        except httpx.TimeoutException:
            print(f"Processing on port {port} exceeded time limit.")
    return None

if __name__ == "__main__":
    # taskProcessor를 별도의 프로세스로 실행
    task_processor_process = multiprocessing.Process(target=taskProcessor)
    task_processor_process.start()
    
    # Quart 애플리케이션을 uvicorn을 사용하여 멀티프로세스로 실행
    config = uvicorn.Config(app=app, host="127.0.0.1", port=5000)
    uvicorn.Server(config).run()