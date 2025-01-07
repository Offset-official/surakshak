import threading
import time 
import datetime
import logging 
import surakshak.utils.inference_engine as inference_engine
from django.core.files import File
from surakshak.utils.notifs import send_all_notifs
from surakshak.utils.logs import MyHandler

logger = logging.getLogger(__name__)
logger.addHandler(MyHandler())


class SystemConfig:
    instrusion_state = ""
    lockdown = False
    incident_id = None

    @classmethod
    def set_intrusion(cls, val):
        cls.instrusion_state = val 
    
    @classmethod
    def get_intrusion(cls):
        return cls.instrusion_state
    
    @classmethod
    def start_state_switch(cls, InferenceSchedule):
        thread = threading.Thread(target=state_switch, daemon=True, name="State Switch", args=[InferenceSchedule])
        thread.start()
    
    @classmethod 
    def toggle(cls):
        if cls.instrusion_state == "ACTIVE":
            cls.instrusion_state = "INACTIVE"
            inference_engine.InferenceEngine.stop()
        elif cls.instrusion_state == "INACTIVE":
            cls.instrusion_state = "ACTIVE"
            inference_engine.InferenceEngine.start()

def state_switch(InferenceSchedule):
    while True:
        logger.info("Running periodic state switch.")
        inactive_schedule = InferenceSchedule.objects.get(pk=1)
        now_time = datetime.datetime.now()
        now_hour = now_time.hour
        now_min = now_time.min 
        now_weekday = now_time.weekday()
        mappings = {
        0: "monday", 1:"tuesday", 2: "wednesday", 3: "thursday", 4:"friday", 5:"saturday", 6:"sunday"
        }
        now_weekday_name = mappings[now_weekday]
        if getattr(inactive_schedule, now_weekday_name):
            # switch does not care about closed days
            inactive_schedule_start_hour = inactive_schedule.start_time.hour
            inactive_schedule_start_min = inactive_schedule.start_time.minute

            inactive_schedule_end_hour = inactive_schedule.end_time.hour
            inactive_schedule_end_min = inactive_schedule.end_time.minute
            
            if SystemConfig.lockdown:
                logger.info("Periodic switch bypassed due to lockdown.")
            elif (now_hour, now_min) == (inactive_schedule_start_hour, inactive_schedule_start_min):
                SystemConfig.set_intrusion("INACTIVE")
                logger.info("System state switched to INACTIVE. Logger sleeping for 120 seconds.")
                # turn off inference engine 
                inference_engine.InferenceEngine.stop()
                time.sleep(120)
                continue 
            elif (now_hour, now_min) == (inactive_schedule_end_hour, inactive_schedule_end_min):
                SystemConfig.set_intrusion("ACTIVE")
                logger.info("System state switched to ACTIVE. Logger sleeping for 120 seconds.")
                # turn on inference engine 
                inference_engine.InferenceEngine.start()
                time.sleep(120)
                continue 
        time.sleep(20)
        continue
        
def enter_lockdown(camera_name, file_obj):
    from surakshak.models import Incident, IncidentType
    SystemConfig.lockdown = True # will disable toggle switch and periodic state switch, boot config is not a problem
    SystemConfig.instrusion_state = "INACTIVE" # for system consistency
    logger.info("ENTERING LOCKDOWN MODE.")
    inference_engine.InferenceEngine.stop() # all camera inferences will stop
    createdIncident = Incident.objects.create(
        incident_type = "Trespassing",
        camera=camera_name,
        resolved = False,
        resolver = None,
        image=file_obj
    )
    SystemConfig.incident_id = createdIncident.id

    # send notifs 
    respondents = IncidentType.objects.filter(type_name="Trespassing").first().respondents.all()
    for respondent in respondents:
        if respondent.is_active:
            print(respondent)   
            # abhinav implement the function below
            send_all_notifs(incident_id=createdIncident.id, incident_type='Trespassing', phone=respondent.phone, email=respondent.email)
                
def resolve_lockdown():
    SystemConfig.lockdown = False 
    SystemConfig.instrusion_state = "ACTIVE"
    SystemConfig.incident_id = None
    inference_engine.InferenceEngine.start() 

    
