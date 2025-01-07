import logging

def add_log(log):
    from surakshak.models import Log 
    Log.objects.create(
        log=log
    )

class MyHandler(logging.Handler):
    def emit(self, record):
        add_log(record.getMessage())
