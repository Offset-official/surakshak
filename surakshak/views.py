from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.views.decorators import gzip
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .utils.camera_manager import CameraManager
import time
from .models import Camera, Incident, Respondent
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.mail import send_mail
from .serializers import IncidentSerializer, RespondentSerializer, IncidentTypeSerializer
from twilio.rest import Client
import os
from dotenv import load_dotenv
from django.templatetags.static import static
import logging 
# import model form 
from .models import InferenceSchedule, Log, IncidentType
from django.forms import ModelForm
from django import forms
from surakshak.utils.system_config import SystemConfig
from django.conf import settings as django_settings
from surakshak.utils.system_config import resolve_lockdown
from surakshak.utils.logs import MyHandler


logger = logging.getLogger(__name__)
logger.addHandler(MyHandler())

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
        # logger.debug(f"Heartbeat check: {status}, Lockdown: {ld}")
        incident_id = SystemConfig.incident_id
        return JsonResponse({'success': True, 'status': status, "lockdown" : ld, "incident_id": incident_id})
    except Exception as e:
        # logger.error(f"Heartbeat error: {e}")
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
        # logger.info(f"System status toggled to: {SystemConfig.instrusion_state}")

        return JsonResponse({'success': True, 'status': SystemConfig.instrusion_state})
    except json.JSONDecodeError:
        # logger.error("Invalid JSON in toggle_status request")
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        # logger.error(f"Toggle status error: {e}")
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

@require_http_methods(["GET", "POST"])
def resolve(request, incident_id):
    """
    Handles the resolution of an intrusion incident.

    GET:
        - If incident exists:
            - If resolved: Show details with "Resolved" message.
            - If not resolved: Show details with "Resolve" button + a dropdown
              to select the responding person.
        - If incident does not exist:
            - Show "Incident not found" message.

    POST:
        - Captures which respondent was selected.
        - Marks the incident as resolved, sets resolver = selected_respondent,
          and redirects to show the updated state.
    """

    try:
        incident_instance = Incident.objects.get(pk=incident_id)
    except Incident.DoesNotExist:
        # Incident not found
        return render(request, "resolve.html", {"incident_found": False})

    # if str(incident_id) != str(SystemConfig.incident_id):
    #     return render(request, "resolve.html", {"incident_found": False})

    if request.method == "POST":
        # Attempt to resolve the incident
        if not incident_instance.resolved:
            selected_respondent = request.POST.get("selected_respondent", "")
            incident_instance.resolved = True
            selected_respondent_instance = Respondent.objects.filter(name=selected_respondent).first()
            incident_instance.resolver = selected_respondent_instance  # Store the name of the resolving respondent
            incident_instance.save()

            # Call your lockdown release function if needed
            resolve_lockdown()

            # Optionally, you can add a success message here (using Django messages framework)
            return redirect('resolve', incident_id=incident_id)
        else:
            # Incident is already resolved; you might want to redirect or show a message
            return redirect('resolve', incident_id=incident_id)

    # GET request
    # Example: retrieve respondents from an IncidentType (like "Trespassing")
    # Adjust the logic here to match your filtering needs
    trespassing_type = IncidentType.objects.filter(type_name="Trespassing").first()
    if trespassing_type:
        respondents = trespassing_type.respondents.all()
        respondent_names = [resp.name for resp in respondents]
    else:
        # Fallback: no matching incident type or no respondents
        respondent_names = []

    context = {
        "incident_found": True,
        "resolved": incident_instance.resolved,
        "incident_type": incident_instance.incident_type,
        "image_url": incident_instance.image.url if incident_instance.image else "",
        "camera_name": incident_instance.camera,
        "incident_time": incident_instance.created_at,
        "incident_id": incident_instance.id,
        "respondent_names": respondent_names,
    }
    # logger.info("Incident image URL: %s", context["image_url"])
    return render(request, "resolve.html", context)

## Settings -> Respondents Page
def respondents_page(request):
    pop_up = request.GET.get("pop_up", "false").lower() == "true"
    return render(request, "settings/respondents.html", {
        "headers": ["ID", "Name", "Phone", "Email", "Active"],
        "respondents": RespondentSerializer(Respondent.objects.all(), many=True).data,
        "pop_up": pop_up,
    })

def add_respondent(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        active = request.POST.get("is_active") == "on"
        respondent = Respondent.objects.create(name=name, phone=phone, email=email, is_active=active)

        respondent.save()
        
    return redirect('respondents_page')

@require_GET
def incidents(request):
    all_incidents = Incident.objects.all().order_by('-created_at')
    return render(request, "incidents.html", {"incidents": all_incidents})