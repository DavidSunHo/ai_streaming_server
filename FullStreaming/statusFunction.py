class WorkerStatus:
    """
    Manages the status of worker processes,
    ensuring thread-safe updates.
    """
    def __init__(self, status_manager, lock):
        """
        Initializes the WorkerStatus with a pool of worker ports,
        a manager for shared state, and a lock for thread safety.

        Args:
            worker_pool: List of worker ports
            manager: Multiprocessing manager for shared state
            lock: Multiprocessing lock for thread safety
        """
        self.status_manager = status_manager
        self.lock = lock

    def getAvailableWorker(self):
        """
        Retrieves an available worker port if one exists.
        Updates the status to False when a worker is allocated.
        
        Returns:
            Available worker port or None if no worker is available
        """
        with self.lock:
            if True in self.status_manager.values(): # 작업 가능한 작업자가 있을 때 
                for port, available in self.status_manager.items():
                    if available:
                        self.status_manager[port] = False  # 작업을 할당할 때 바로 상태를 업데이트
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
            self.status_manager[port] = status # 특정 포트의 상태를 업데이트