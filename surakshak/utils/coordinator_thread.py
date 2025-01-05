import threading

class CoordinatorThread:
    def __init__(self, func):
        self.thread = threading.Thread(target=func, daemon=True)
        self.thread.start()
        