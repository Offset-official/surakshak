from django.shortcuts import render
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.views.decorators import gzip
from django.views.decorators.http import require_GET, require_POST
from .utils.camera_manager import CameraManager
import time
from .models import Camera, Incident, Respondent
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.mail import send_mail
from .serializers import IncidentSerializer, RespondentSerializer
from twilio.rest import Client
import os
from dotenv import load_dotenv
from django.templatetags.static import static
import logging 
# import model form 
from .models import InferenceSchedule, Log
from django.forms import ModelForm
from django import forms
from surakshak.utils.system_config import SystemConfig

logger = logging.getLogger(__name__)

def homepage(request):
    return render(request, "homepage.html")


@require_GET
def heartbeat(request):
    """
    Returns the current system status.
    Expected response format: {'success': True, 'status': 'ACTIVE'/'INACTIVE', 'lockdown': True/False}
    """
    try:
        status = SystemConfig.instrusion_state
        ld = SystemConfig.lockdown
        logger.debug(f"Heartbeat check: {status}, Lockdown: {ld}")
        incident_id = SystemConfig.incident_id
        return JsonResponse({'success': True, 'status': status, "lockdown" : ld, "incident_id": incident_id})
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to retrieve system status'}, status=500)


@gzip.gzip_page
def video_feed(request, camera_name):
    # Define your stream names corresponding to feed_number
    if not camera_name:
        return HttpResponse("Invalid video feed", status=404)
    camera = CameraManager.get_camera(camera_name)

    if not camera:
        return HttpResponse("Stream not found.", status=404)

    try:
        return StreamingHttpResponse(
            generate_frames(camera),
            content_type="multipart/x-mixed-replace; boundary=frame",
        )
    except Exception as e:
        print(f"Error in video feed: {str(e)}")
        return HttpResponse("Error accessing video stream", status=500)


def generate_frames(camera):
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        else:
            # If no frame is available, wait briefly
            time.sleep(0.1)


def stream_page(request):
    # get names of 3 cameras
    cctvs = Camera.objects.all()[:3]
    cctvNames = [cctv.name for cctv in cctvs]
    return render(request, "streams.html", {"cctvs": cctvNames})


def notify_page(request):
    return render(request, "notify.html")


def logs_page(request):
    logs = Log.objects.all().order_by("-created_at")
    return render(request, "logs.html", {"logs": logs})


def settings(request):
    return render(request, "settings.html")


@require_POST
def toggle_status(request):
    """
    Toggles the system status based on the request.
    Expects JSON body: {'state': True/False}
    """
    try:
        SystemConfig.toggle()
        logger.info(f"System status toggled to: {SystemConfig.instrusion_state}")

        return JsonResponse({'success': True, 'status': SystemConfig.instrusion_state})
    except json.JSONDecodeError:
        logger.error("Invalid JSON in toggle_status request")
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Toggle status error: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to toggle system status'}, status=500)

def notify_api(
    request,
):  # TODO modularize this function and break it into smaller functions
    if request.method == "POST":
        try:
            print(f"Sending notifications...")
            data = json.loads(request.body)
            modes = data.get("modes", [])
            incident_groups = data.get("incident_groups", [])
            # empty means all groups

            incident = Incident.objects.latest("created_at")  # get the latest incident

            # Serialize the incident data
            incident_data = IncidentSerializer(incident).data

            if not modes:
                modes = ["email", "sms", "call", "whatsapp"]
            if not incident_groups:
                incident_groups = ["trespassing", "fire", "idk"]

            # TODO get all the respondents from the given groups

            Respondents = RespondentSerializer(Respondent.objects.all(), many=True).data
            sample_url = "https://www.incident_page.com"
            main_text = f"Dear Surakshak,\n\nPlease check out the incident snippet and other information at {sample_url} to resolve the alert as soon as possible.  \n\nRegards, \nInstitution"
            subject = f"Alert! Incident Type: {incident_data['incident_type']} Detected at {incident_data['camera']}"
            phnumbers = [respondent["phone"] for respondent in Respondents]
            account_sid = os.getenv("WHATSAPP_ACCOUNT_SID")
            auth_token = os.getenv("WHATSAPP_AUTH_TOKEN")

            if "email" in modes:
                mails = [respondent["email"] for respondent in Respondents]
                message = (
                    subject,
                    main_text,
                    "abhinavkun26@gmail.com",
                    mails,
                )
                send_mail(*message, fail_silently=False)
            client = Client(account_sid, auth_token)
            phnumbers = ["7014206208"]
            if "sms" in modes:
                for receiver_number in phnumbers:
                    message = client.messages.create(
                        from_="+12317666829",
                        body="Alert! Incident Type: Trespassing Detected at  Camera 1",
                        to=f"+91{receiver_number}",
                    )

            if "whatsapp" in modes:
                for receiver_number in phnumbers:
                    message = client.messages.create(
                        from_="whatsapp:+14155238886",
                        content_sid="HXb5b62575e6e4ff6129ad7c8efe1f983e",
                        content_variables='{"1":"12/1","2":"3pm"}',
                        to=f"whatsapp:+91{receiver_number}",
                    )

            if "call" in modes:
                url = os.getenv("TwiML_BIN_URL")
                voice_url = static("voice.xml")
                for receiver_number in phnumbers:
                    call = client.calls.create(
                        from_="+12317666829",
                        to=f"+91{receiver_number}",
                        url={url},
                    )

            print("Notifications sent successfully!")
            return JsonResponse(
                {
                    "success": True,
                    "message": "Notifications sent successfully",
                }
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse(
        {"success": False, "error": "Invalid request method"}, status=405
    )


def timings_page(request):
    # create model form 
    class InferenceScheduleForm(ModelForm):
        class Meta:
            model = InferenceSchedule
            fields = "__all__" 
            widgets = {
                'start_time': forms.TimeInput(attrs={'type': 'time'}),
                'end_time': forms.TimeInput(attrs={'type': 'time'}),
                'monday': forms.CheckboxInput(),
                'tuesday': forms.CheckboxInput(),
                'wednesday': forms.CheckboxInput(),
                'thursday': forms.CheckboxInput(),
                'friday': forms.CheckboxInput(),
                'saturday': forms.CheckboxInput(),
                'sunday': forms.CheckboxInput(),
            }  


    schedule = InferenceSchedule.objects.get(pk=1)
    
    if request.method == "POST":
        form = InferenceScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            return render(request, "timings.html", {"form": form, "success": True})
        return JsonResponse({"success": False, "error": form.errors}, status=400)
    elif request.method == "GET":
        form = InferenceScheduleForm(instance=schedule)
        # render the form
        return render(request, "timings.html", {"form": form})





    inferenceSchedule = form.objects.get(pk=1)


    return render(request, "timings.html")

def resolve(request, incident_id):
    return render(request, "layout.html")