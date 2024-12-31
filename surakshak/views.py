# your_app/views.py

from django.shortcuts import render
from django.http import StreamingHttpResponse, HttpResponse
from django.views.decorators import gzip
from .utils.camera_manager import CameraManager
import time
from .models import *

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
            generate_frames(camera), content_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        print(f"Error in video feed: {str(e)}")
        return HttpResponse("Error accessing video stream", status=500)


def generate_frames(camera):
    while True:
        frame = camera.get_frame()
        if frame:
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            )
        else:
            # If no frame is available, wait briefly
            time.sleep(0.1)


def stream_page(request):
    # get names of 3 cameras
    cctvs = Cameras.objects.all()[:3]
    cctvNames = [cctv.name for cctv in cctvs]
    return render(request, "stream.html", {"cctvs": cctvNames})


## For respondents settings page

def respondents_page(request):
    return render(request, "settings/respondents.html", {
        "headers" : ["ID", "Group", "Name", "Phone", "Email", "Active"],
        "respondents" : Respondents.objects.all()
    })

def respondent_reg_page(request):

    incidents = Incidents_types.objects.all()
    return render(request, "settings/respondent_registration.html", {'incidents': incidents})

def add_respondent(request):
    if request.method == "POST":
        group_id = request.POST.get("group")  # This gets the ID as a string
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        is_active = request.POST.get("is_active") == "on"  # Handle checkbox correctly
        
        try:
            # Fetch the Incidents_types instance
            group = Incidents_types.objects.get(id=group_id)
            
            # Create a new Respondents record
            record = Respondents(
                group=group,
                name=name,
                phone=phone,
                email=email,
                is_active=is_active
            )
            record.save()
        except Incidents_types.DoesNotExist:
            # Handle the case where the group ID is invalid
            return HttpResponse("Invalid incident type selected", status=400)
        
    return render(request, 'settings/respondents.html', {
        "respondents": Respondents.objects.all(),
    })

