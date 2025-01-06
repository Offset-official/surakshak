import threading

class CoordinatorThread:
    def __init__(self, func, camera_name):
        self.thread = threading.Thread(target=func, daemon=True, args=[camera_name])
        self.thread.start()
        