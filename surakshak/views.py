from django.shortcuts import render
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.views.decorators import gzip
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


def homepage(request):
    return render(request, "homepage.html")


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
    return render(request, "logs.html")


def settings(request):
    return render(request, "settings.html")


@csrf_exempt
def toggle_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            state = data.get("state", False)
            request.session["toggle_state"] = state
            if state:
                pass
                # Subham you may start your inference engine here
            return JsonResponse({"success": True, "state": state})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    elif request.method == "GET":
        # Return the stored state
        state = request.session.get("toggle_state", False)
        return JsonResponse({"success": True, "state": state})
    return JsonResponse(
        {"success": False, "error": "Invalid request method"}, status=405
    )


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
