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
            return {"status": "error", "message": "empty que"} # 비어있으면 None 반환