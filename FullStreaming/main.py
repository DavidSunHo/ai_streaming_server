from quart import Quart, websocket
from uvicorn import Server, Config
from taskFunction import TaskQueue
from statusFunction import WorkerStatus
from httpx import Client, TimeoutException
from multiprocessing import Manager, Process, freeze_support


# Quart 초기화
app = Quart(__name__)


def taskProcessor(task_queue, worker_status, result_queue):
    """
    Processes tasks from the task queue and assigns them to available workers.

    Args:
        task_queue: The task queue to retrieve tasks from
        worker_status: The WorkerStatus to manage worker availability
    """
    ##TODO: WebSocket이 붙었을 때만 가동되게씀 하려면 @app.websocket("/process-tasks")를 추가하여 핸들러 내부로 만들어야함
    while True:
        ## 큐에서 image를 읽어옴
        task = task_queue.get()
        ## 큐에 image가 있으면
        if task is not None:
            p = Process(target=handleImageProcessing, args=(task, worker_status, result_queue))
            p.start() # 병렬로 작업을 할당
            p.join()


def handleImageProcessing(task, worker_status, result_queue):
    """
    Handles image processing by sending the image to a worker and updating the worker status.

    Args:
        image_bytes: The image data to process
        port: The port of the worker to process the image
        worker: The WorkerStatus instance to update the worker status
    """
    try:
        ## 서브 서버로 image 분배
        available_worker_port = worker_status.getAvailableWorker()  # 가용한 worker_port 가져오기
        if available_worker_port is not None:
            result = processOnWorker(task, available_worker_port)
        
            ## 결과값 result_queue에 저장  
            if result:
                result_queue.put({"status": "processing", "processed_image": result})
            else:
                result_queue.put({"status": "error", "message": "Processing failed"})
                
            worker_status.upDateStatus(available_worker_port, True)
        else:
            print("no available port")
    
    except Exception as e:
            print(f"Error in taskProcessor: {e}")


def processOnWorker(image_data, port):
    """
    Send image data to a worker process for processing and returns the result.

    Args:
        image_data: The image data to process
        port: The port of the worker to process the image

    Returns:
        The processed image result or None if processing fails
    """
    url = f"http://localhost:{port}/process"
    headers = {"Content-Type": "application/octet-stream"}

    with Client() as client:
        try:
            response = client.post(url, content=image_data, headers=headers, timeout=4.0)
            if response.status_code == 200:
                result = response.json()["processed_image"]
                # print(f"Processed image on port {port}: {result}")
                return result
            else:
                print(f"Failed to process image on port {port}: {response.status_code}")
        except TimeoutException:
            print(f"Processing on port {port} exceeded time limit.")
    return None


def runUvicorn(task_queue, result_queue):
    """
    Run the Uvicorn server with the specified task queue.

    Args:
        task_queue: The task queue to use in the WebSocket handler
    """
    
    @app.websocket("/upload")
    async def upload():
        """
        WebSocket endpoint for uploading images. Receives image data,
        converts it to bytes, and adds it to the task queue.
        """
        while True:
            data = await websocket.receive_json() # 데이터 받는 부분
            task_queue.add(bytes.fromhex(data["image"])) # TaskQueue Actor에 데이터를 넣는 부분
            
            await websocket.send_json(result_queue.get())
                
    config = Config(app=app, host="localhost", port=5000)
    Server(config).run()
    
        
if __name__ == "__main__":
    freeze_support()  # Windows에서 multiprocessing을 사용할 때 필요
    
    # 공유 큐를 저장할 매니저 객체 생성
    manager = Manager()
    
    # WorkerStatus 클래스의 상태 업데이트를 보호
    lock = manager.Lock()  # Manager를 통해 공유 락 생성
    
    # 공유 큐 생성
    shared_queue = manager.Queue() # Input Data
    shared_result_queue = manager.Queue() # Output Data
    
    # 작업자 풀 생성
    worker_pool = [8000, 8001] #, 8002, 8003, 8004
    status_manager = manager.dict({port: True for port in worker_pool})

    # WorkerStatus와 TaskQueue Actor 인스턴스 생성
    worker_status = WorkerStatus(status_manager, lock)
    task_queue = TaskQueue(shared_queue)
    
    # Quart 애플리케이션을 uvicorn을 사용하여 멀티프로세스로 실행
    uvicorn_process = Process(target=runUvicorn, args=(task_queue, shared_result_queue))
    uvicorn_process.start()
    
    # taskProcessor를 별도의 프로세스로 실행
    task_processor_process = Process(target=taskProcessor, args=(task_queue, worker_status, shared_result_queue))
    task_processor_process.start()

    # 두 프로세스가 종료될 때까지 대기
    task_processor_process.join()
    uvicorn_process.join()