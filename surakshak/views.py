from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators import gzip
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .utils.camera_manager import CameraManager
import time
from .models import Camera, Incident, Respondent
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.mail import send_mail
from .serializers import (
    IncidentSerializer,
    RespondentSerializer,
    IncidentTypeSerializer,
    CameraSerializer,
)
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
from django.contrib import messages
from surakshak.utils.camera_manager import CameraManager
import cv2
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from surakshak.utils.notifs import (
    send_call_notification,
    send_email_notification,
    send_sms_notification,
    send_whatsapp_notification,
)


logger = logging.getLogger(__name__)
logger.addHandler(MyHandler())


def login_page(request):
    next_url = request.GET.get("next", "homepage")
    if request.user.is_authenticated:
        return render(request, "homepage.html")
    return render(request, "auth_page.html", {"next": next_url})


def login(request):
    username = request.POST.get("username")
    password = request.POST.get("password")
    user = authenticate(request, username=username, password=password)
    next_url = request.POST.get("next", "homepage")

    if user is not None:
        auth_login(request, user)
        return redirect(next_url)
    else:
        return render(request, "auth_page.html", {"error": "Invalid credentials"})


def homepage(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=homepage")
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

        return JsonResponse(
            {
                "success": True,
                "status": status,
                "lockdown": ld,
                "incident_id": incident_id,
            }
        )
    except Exception as e:
        # logger.error(f"Heartbeat error: {e}")
        return JsonResponse(
            {"success": False, "error": "Failed to retrieve system status"}, status=500
        )


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
    cctvs = Camera.objects.all()
    cctvNames = [cctv.name for cctv in cctvs]
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=stream_page")
    return render(request, "streams.html", {"cctvs": cctvNames})


def notify_page(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=notify_page")
    return render(request, "notify.html")


def logs_page(request):
    logs = Log.objects.all().order_by("-created_at")
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=logs_page")
    return render(request, "logs.html", {"logs": logs})


def settings_page(request):
    active_tab = request.GET.get("tab", "respondents")  # Default to 'respondents'
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=settings")
    return render(request, "settings.html", {"active_tab": active_tab})


@require_POST
def toggle_status(request):
    """
    Toggles the system status based on the request.
    Expects JSON body: {'state': True/False}
    """
    try:
        SystemConfig.toggle()
        # logger.info(f"System status toggled to: {SystemConfig.instrusion_state}")

        return JsonResponse({"success": True, "status": SystemConfig.instrusion_state})
    except json.JSONDecodeError:
        # logger.error("Invalid JSON in toggle_status request")
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        # logger.error(f"Toggle status error: {e}")
        return JsonResponse(
            {"success": False, "error": "Failed to toggle system status"}, status=500
        )


def notify_api(
    request,
):
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

            Respondents = RespondentSerializer(Respondent.objects.all(), many=True).data

            url = reverse("resolve", args=[incident_data["id"]])
            main_text = f"Dear Surakshak,\n\nPlease check out the incident snippet and other information at {url} to resolve the alert as soon as possible.  \n\nRegards, \nInstitution"
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
                "start_time": forms.TimeInput(attrs={"type": "time"}),
                "end_time": forms.TimeInput(attrs={"type": "time"}),
                "monday": forms.CheckboxInput(),
                "tuesday": forms.CheckboxInput(),
                "wednesday": forms.CheckboxInput(),
                "thursday": forms.CheckboxInput(),
                "friday": forms.CheckboxInput(),
                "saturday": forms.CheckboxInput(),
                "sunday": forms.CheckboxInput(),
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
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login_page')}?next=timings")
        return render(request, "timings.html", {"form": form})

    inferenceSchedule = form.objects.get(pk=1)

    return render(request, "timings.html")


def camera_page(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=camera_page")
    pop_up = request.GET.get("pop_up", "false").lower() == "true"
    return render(
        request,
        "settings/camera_mod.html",
        {
            "headers": ["ID", "Name", "Location", "RTSP-URL"],
            "respondents": CameraSerializer(Camera.objects.all(), many=True).data,
            "pop_up": pop_up,
        },
    )


def add_camera(request):
    if request.method == "POST":
        name = request.POST.get("name")
        location = request.POST.get("location")
        rtsp_url = request.POST.get("rtsp_url")
        camera = Camera.objects.create(name=name, location=location, rtsp_url=rtsp_url)

        camera.save()

    return redirect("camera_page")


## Settings -> Respondents Page
def respondents_page(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=respondents_page")
    pop_up = request.GET.get("pop_up", "false").lower() == "true"
    return render(
        request,
        "settings/respondents.html",
        {
            "headers": ["ID", "Name", "Phone", "Email", "Active"],
            "respondents": RespondentSerializer(
                Respondent.objects.all(), many=True
            ).data,
            "pop_up": pop_up,
        },
    )


def add_respondent(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        active = request.POST.get("is_active") == "on"
        respondent = Respondent.objects.create(
            name=name, phone=phone, email=email, is_active=active
        )

        respondent.save()

    return redirect("respondents_page")


## Settings -> Incidents Mapping Page
def incidents_mapping_page(request):
    pop_up = request.GET.get("pop_up", "false").lower() == "true"
    incident_type = request.GET.get("incident_type", "")
    incident_types = IncidentType.objects.all()
    serialized_incidents = IncidentTypeSerializer(incident_types, many=True).data

    ## Filtering for tresspassing
    tresspassing_ids = IncidentType.objects.filter(
        type_name="Tresspassing"
    ).values_list("id", flat=True)

    tress_avail_respondents = Respondent.objects.exclude(
        incident_types__in=tresspassing_ids
    )
    tress_avail_serialized = RespondentSerializer(
        tress_avail_respondents, many=True
    ).data

    ## Filtering for fire
    fire_ids = IncidentType.objects.filter(type_name="Fire").values_list(
        "id", flat=True
    )
    fire_avail_respondents = Respondent.objects.exclude(incident_types__in=fire_ids)
    fire_avail_serialized = RespondentSerializer(fire_avail_respondents, many=True).data

    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=incidents_mapping_page")

    return render(
        request,
        "settings/incidents_map.html",
        {
            "incident_mappings": serialized_incidents,
            "available_tress_respondents": tress_avail_serialized,
            "available_fire_respondents": fire_avail_serialized,
            "pop_up": pop_up,
            "incident_type": incident_type,
        },
    )


def assign_respondent(request):
    if request.method == "POST":
        type_name = request.POST.get("incident_type")
        selected_respondents = request.POST.getlist(
            "selected_respondents"
        )  # Retrieve selected IDs

        for respondent in selected_respondents:
            name = respondent
            # Validate that the respondent exists
            try:
                respondent = Respondent.objects.get(name=name)
            except Respondent.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Respondent does not exist"}, status=400
                )

            # Check if the incident type exists
            incident_type, created = IncidentType.objects.get_or_create(
                type_name=type_name
            )

            # Check if the respondent is already assigned
            if incident_type.respondents.filter(id=respondent.id).exists():
                return JsonResponse(
                    {"success": False, "error": "Respondent already assigned"},
                    status=400,
                )

            # Add the respondent to the incident type
            incident_type.respondents.add(respondent)

    return redirect("incidents_mapping_page")


@require_http_methods(["GET", "POST"])
def resolve(request, incident_id):
    """
    Handles the resolution of an intrusion incident.

    GET:
        - If incident exists:
            - If resolved: Show details with "Resolved" message and resolver's name.
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

    if request.method == "POST":
        # Attempt to resolve the incident
        if not incident_instance.resolved:
            selected_respondent = request.POST.get("selected_respondent", "")
            if not selected_respondent:
                # No respondent selected
                logger.warning("No respondent selected for resolving the incident.")
                return render(
                    request,
                    "resolve.html",
                    {
                        "incident_found": True,
                        "resolved": False,
                        "incident_type": incident_instance.incident_type,
                        "image_url": (
                            incident_instance.image.url
                            if incident_instance.image
                            else ""
                        ),
                        "camera_name": incident_instance.camera,
                        "incident_time": incident_instance.created_at,
                        "incident_id": incident_instance.id,
                        "respondent_names": get_respondent_names(),
                        "error_message": "Please select a respondent to resolve the incident.",
                    },
                )

            selected_respondent_instance = Respondent.objects.filter(
                name=selected_respondent
            ).first()
            if not selected_respondent_instance:
                # Respondent does not exist
                logger.warning(
                    f"Selected respondent '{selected_respondent}' does not exist."
                )
                return render(
                    request,
                    "resolve.html",
                    {
                        "incident_found": True,
                        "resolved": False,
                        "incident_type": incident_instance.incident_type,
                        "image_url": (
                            incident_instance.image.url
                            if incident_instance.image
                            else ""
                        ),
                        "camera_name": incident_instance.camera,
                        "incident_time": incident_instance.created_at,
                        "incident_id": incident_instance.id,
                        "respondent_names": get_respondent_names(),
                        "error_message": "Selected respondent does not exist.",
                    },
                )

            # Mark the incident as resolved
            incident_instance.resolved = True
            incident_instance.resolver = selected_respondent_instance  # Assuming resolver is a ForeignKey to Respondent
            incident_instance.save()

            # Call your lockdown release function if needed
            resolve_lockdown()

            logger.info(
                f"Incident {incident_id} resolved by {selected_respondent_instance.name}."
            )

            # Optionally, add a success message using Django messages framework
            # messages.success(request, "Incident resolved successfully.")

            return redirect("resolve", incident_id=incident_id)
        else:
            # Incident is already resolved; you might want to redirect or show a message
            return redirect("resolve", incident_id=incident_id)

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

    # If the incident is resolved, get the resolver's name
    resolver_name = (
        incident_instance.resolver.name if incident_instance.resolver else ""
    )

    context = {
        "incident_found": True,
        "resolved": incident_instance.resolved,
        "incident_type": incident_instance.incident_type,
        "image_url": incident_instance.image.url if incident_instance.image else "",
        "camera_name": incident_instance.camera,
        "incident_time": incident_instance.created_at,
        "incident_id": incident_instance.id,
        "respondent_names": respondent_names,
        "resolver_name": resolver_name,  # Add resolver's name to context
    }
    # logger.info("Incident image URL: %s", context["image_url"])
    return render(request, "resolve.html", context)


def get_respondent_names():
    """
    Helper function to retrieve respondent names.
    Adjust the logic based on how respondents are related to IncidentType.
    """
    trespassing_type = IncidentType.objects.filter(type_name="Trespassing").first()
    if trespassing_type:
        respondents = trespassing_type.respondents.all()
        return [resp.name for resp in respondents]
    return []


@require_GET
def incidents(request):
    all_incidents = Incident.objects.all().order_by("-created_at")
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=incidents")
    return render(request, "incidents.html", {"incidents": all_incidents})


@require_http_methods(["GET", "POST"])
def adjust_camera(request, camera_name=None):
    """
    Adjust settings for a specific camera without needing to select from a dropdown.

    URL pattern example:
      path("adjust_camera/<str:camera_name>/", views.adjust_camera, name="adjust_camera")

    Args:
        request (HttpRequest): The incoming request.
        camera_name (str): Name of the camera to adjust.

    Returns:
        HttpResponse: Rendered template with context or redirect on actions.
    """
    # If no camera name is supplied, you can decide what to do:
    # - show an error, or
    # - redirect to a page explaining no camera was selected, etc.
    if not camera_name:
        messages.error(request, "No camera name specified.")
        return redirect("home")  # Replace "home" with your homepage or another view

    # Retrieve the camera object by name
    camera = get_object_or_404(Camera, name=camera_name)

    # Put camera in context for the template
    context = {
        "selected_camera": camera,
        "camera_name": camera_name,
    }

    if request.method == "POST":
        # 1) Capture Snapshot
        if "capture_snapshot" in request.POST:
            frame = CameraManager._cameras[camera.name].frame

            if frame is None:
                messages.error(
                    request,
                    "Failed to capture image from the camera. Is the camera streaming?",
                )
                return redirect("adjust_camera", camera_name=camera_name)

            # Encode frame to JPEG
            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                messages.error(request, "Failed to encode the captured image.")
                return redirect("adjust_camera", camera_name=camera_name)

            image_data = buffer.tobytes()
            image_name = f"camera_{camera.id}_snapshot.jpg"
            image_path = os.path.join("snapshots", image_name)

            # Save the image in MEDIA_ROOT/snapshots/
            full_path = os.path.join(django_settings.MEDIA_ROOT, "snapshots")
            os.makedirs(full_path, exist_ok=True)
            file_path = os.path.join(full_path, image_name)
            with open(file_path, "wb") as f:
                f.write(image_data)

            # Add snapshot URL to context
            context["snapshot_url"] = os.path.join(
                django_settings.MEDIA_URL, "snapshots", image_name
            )
            return render(request, "camera_adjust.html", context)

        # 2) Save Coordinates
        elif "save_coordinates" in request.POST:
            x1 = request.POST.get("x1")
            y1 = request.POST.get("y1")
            x2 = request.POST.get("x2")
            y2 = request.POST.get("y2")

            if not all([x1, y1, x2, y2]):
                messages.error(request, "All coordinate fields are required.")
                return redirect("adjust_camera", camera_name=camera_name)

            # Validate and save coordinates
            try:
                camera.x1 = float(x1)
                camera.y1 = float(y1)
                camera.x2 = float(x2)
                camera.y2 = float(y2)
                camera.save()
                messages.success(request, "Coordinates saved successfully.")
            except ValueError:
                messages.error(request, "Invalid coordinate values.")
            return redirect("adjust_camera", camera_name=camera_name)

    return render(request, "camera_adjust.html", context)


@require_http_methods(["GET"])
def single_stream_page(request, camera_name):
    """
    Displays a single camera's stream based on the selected camera name.
    """
    # Retrieve the camera instance or return 404 if not found
    camera = get_object_or_404(Camera, name=camera_name)

    context = {
        "camera_name": camera.name,
    }
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_page')}?next=single_stream_page")
    return render(request, "single_stream.html", context)
