import threading

class CoordinatorThread:
    def __init__(self, *args):
        self.thread = threading.Thread(target=args[0], daemon=True, args=args[1:])
        self.thread.start()
        