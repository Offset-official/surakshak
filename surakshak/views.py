from django.shortcuts import render
from django.http import StreamingHttpResponse
from django.views.decorators import gzip
from .utils.camera import VideoCamera, gen


def homepage(request):
    return render(request, "homepage.html")


# RTSP urls hosted on the internet for testing
# rtsp_url = "rtsp://rtspstream:953083142923da6e035f35315bb1f820@zephyr.rtsp.stream/pattern"  # recording pattern
# rtsp_url = "rtsp://rtspstream:d5ab2b139298242744eb19ac2b47854d@zephyr.rtsp.stream/movie"  ## big buck bunny

# RTSP urls locally hosted
# rtsp_url = "rtsp://your-ip-address>:8554/<video-name>" # rtsp stream template
# examples
# rtsp_url = "rtsp://192.168.29.10:8554/stream1"


@gzip.gzip_page
def video_feed(request, feed_number):
    rtsp_urls = {
        1: "rtsp://192.168.29.10:8554/stream1",
        2: "rtsp://192.168.29.10:8554/stream2",
        3: "rtsp://192.168.29.10:8554/stream3",
    }

    rtsp_url = rtsp_urls.get(feed_number)

    if not rtsp_url:
        return StreamingHttpResponse("Invalid video feed", status=404)

    try:
        cam = VideoCamera(rtsp_url)
        return StreamingHttpResponse(
            gen(cam), content_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        print(f"Error in video feed: {str(e)}")
        return StreamingHttpResponse("Error accessing video stream")


def stream_page(request):
    cctvs = [
        1,
        2,
        3,
    ]

    return render(request, "stream.html", {"cctvs": cctvs})
