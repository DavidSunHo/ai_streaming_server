import ray
import asyncio
from quart import Quart, websocket
from uvicorn import Server, Config
from httpx import Client, TimeoutException
from multiprocessing import Manager, Process, freeze_support, Lock

# Quart 초기화
app = Quart(__name__)

# Ray 초기화
ray.init(ignore_reinit_error=True)


class WorkerStatus:
    """
    Manages the status of worker processes,
    ensuring thread-safe updates.
    """
    def __init__(self, worker_pool, manager, lock):
        """
        Initializes the WorkerStatus with a pool of worker ports,
        a manager for shared state, and a lock for thread safety.

        Args:
            worker_pool: List of worker ports
            manager: Multiprocessing manager for shared state
            lock: Multiprocessing lock for thread safety
        """
        self.status = manager.dict({port: True for port in worker_pool}) # 초기화 시 worker_pool에 있는 포트들을 사용하여 상태를 True로 설정
        self.lock = lock
        print(self.status)
        
    def getAvailableWorker(self):
        """
        Retrieves an available worker port if one exists.
        Updates the status to False when a worker is allocated.
        
        Returns:
            Available worker port or None if no worker is available
        """
        with self.lock:
            if True in self.status.values(): # 작업 가능한 작업자가 있을 때 
                for port, available in self.status.items():
                    if available:
                        self.status[port] = False  # 작업을 할당할 때 바로 상태를 업데이트
                        return port
            else: # 작업 가능자가 없을 때
                return None
        
    def upDateStatus(self, port, status):
        """Updates the status of a specific worker port.

        Args:
            port: The worker port to update
            status: The new status to set
        """
        with self.lock:
            self.status[port] = status # 특정 포트의 상태를 업데이트


class TaskQueue:
    """
    Manages a queue of tasks to be processed.
    """
    def __init__(self, shared_queue):
        """
        Initializes the TaskQueue with a shared queue.
        
        :param shared_queue: The shared queue to manage tasks
        """
        self.queue = shared_queue

    def add(self, item):
        """
        Adds an item to the queue.
        
        :param item: The item to add to the queue
        """
        self.queue.put(item) # 큐에 항목 추가
        
    def view(self,):
        """
        Returns the size of the queue.
        
        :return: The size of the queue
        """
        return self.queue.qsize() # 큐의 크기를 반환

    def get(self,):
        """
        Retrieves an item from the queue in a non-blocking manner.
        
        :return: The item from the queue or None if the queue is empty
        """
        if self.queue.qsize() > 0:
            return self.queue.get_nowait() # non-block 방식으로 큐에서 항목을 가져옴.
        else: 
            return None # 비어있으면 None 반환
        

def create_upload_handler(task_queue):
    """
    Creates a WebSocket handler for uploading images.

    Args:
        task_queue: The task queue to add received images to
    """
    @app.websocket("/upload")
    async def upload():
        """
        WebSocket endpoint for uploading images. Receives image data,
        converts it to bytes, and adds it to the task queue.
        """
        while True:
            data = await websocket.receive_json() # 데이터 받는 부분

            image_bytes = bytes.fromhex(data["image"]) # 받은 데이터 바이트로 변환

            await task_queue.add(image_bytes) # Ray의 TaskQueue Actor에 데이터를 넣는 부분

            ##TODO: input 데이터 확인하는 TEST 코드
            length = task_queue.view()
            print(f"upload() queue length: {length}")
    

def taskProcessor(task_queue, worker_status):
    """
    Processes tasks from the task queue and assigns them to available workers.

    Args:
        task_queue: The task queue to retrieve tasks from
        worker_status: The WorkerStatus to manage worker availability
    """
    while True:
        ##TODO: input 데이터 확인하는 TEST 코드
        # length = task_queue.view()
        # print(f"taskProcessor() queue length: {length}")
        
        try:
            task = task_queue.get() # Q에서 데이터 가져오기
            
            available_worker_port = worker_status.getAvailableWorker()  # 가용한 worker_port 가져오기
            if available_worker_port is not None:
                handleImageProcessing.remote(task, available_worker_port, worker_status) # 작업자가 있을 때 병렬로 할당  
        except Exception as e:
            print(f"Error in taskProcessor: {e}")

          
@ray.remote
def handleImageProcessing(image_bytes, port, worker):
    """
    Handles image processing by sending the image to a worker and updating the worker status.

    Args:
        image_bytes: The image data to process
        port: The port of the worker to process the image
        worker: The WorkerStatus instance to update the worker status
    """
    result = processOnWorker.remote(image_bytes, port)
    if result:
        asyncio.run(websocket.send_json({"status": "processing", "processed_image": result}))
    else:
        asyncio.run(websocket.send_json({"status": "error", "message": "Processing failed"}))
    worker.updateStatus(port, True)
        
        
@ray.remote
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
            response = client.post(url, content=image_data, headers=headers, timeout=2.5)
            if response.status_code == 200:
                result = response.json()["processed_image"]
                print(f"Processed image on port {port}: {result}")
                return result
            else:
                print(f"Failed to process image on port {port}: {response.status_code}")
        except TimeoutException:
            print(f"Processing on port {port} exceeded time limit.")
    return None


def runUvicorn(task_queue):
    """
    Run the Uvicorn server with the specified task queue.

    Args:
        task_queue: The task queue to use in the WebSocket handler
    """
    create_upload_handler(task_queue)
    config = Config(app=app, host="localhost", port=5000)
    Server(config).run()
    

if __name__ == "__main__":
    # 공유 큐를 저장할 매니저 객체 생성
    manager = Manager()
    
    # WorkerStatus 클래스의 상태 업데이트를 보호
    lock = Lock()
    
    # 공유 큐 생성
    shared_queue = manager.Queue()
    
    # 작업자 풀 생성  
    worker_pool = [8000, 8001, 8002, 8003, 8004] 

    # WorkerStatus와 TaskQueue Actor 인스턴스 생성
    worker_status = WorkerStatus(worker_pool, manager, lock)
    task_queue = TaskQueue(shared_queue)
    
    # Quart 애플리케이션을 uvicorn을 사용하여 멀티프로세스로 실행
    uvicorn_process = Process(target=runUvicorn, args=(task_queue,))
    uvicorn_process.start()
    
    # taskProcessor를 별도의 프로세스로 실행
    task_processor_process = Process(target=taskProcessor, args=(task_queue, worker_status,))
    task_processor_process.start()

    # 두 프로세스가 종료될 때까지 대기
    task_processor_process.join()
    uvicorn_process.join()