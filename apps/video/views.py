import io
import os
import cv2
import numpy as np
from PIL import Image, ImageOps
from django.http import StreamingHttpResponse, JsonResponse
from moviepy import VideoFileClip, AudioFileClip
import ffmpeg
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status


class VideoGenerationView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        if 'background' not in request.FILES:
            return Response({"error": "Background image is required"}, status=status.HTTP_400_BAD_REQUEST)

        background = Image.open(request.FILES['background']).convert("RGBA")
        width, height = background.size
        fps = int(request.data.get("fps", 30))

        intro_folder = "/home/ubuntu/mult/data_for_video/intro"
        main_folder = "/home/ubuntu/mult/data_for_video/main"
        audio_path = "/home/ubuntu/mult/data_for_video/audio.wav"

        def load_images_from_folder(folder):
            images = []
            if not os.path.exists(folder):
                return images
            files = sorted(os.listdir(folder))
            for filename in files:
                if filename.endswith(".png"):
                    img = Image.open(os.path.join(folder, filename)).convert("RGBA")
                    img = ImageOps.expand(img, border=2, fill=(0, 0, 0, 0))
                    images.append(img)
            return images

        def blend_images(base, overlay):
            base = base.convert("RGBA")
            overlay = overlay.convert("RGBA")
            temp = Image.new("RGBA", base.size, (0, 0, 0, 0))
            temp.paste(overlay, (0, 0), overlay)
            return Image.alpha_composite(base, temp)

        intro_frames = load_images_from_folder(intro_folder)
        main_frames = load_images_from_folder(main_folder)

        output_buffer = io.BytesIO()

        # Используем ffmpeg для создания видео в памяти
        process = (
            ffmpeg
            .input('pipe:0', format='rawvideo', pix_fmt='rgb24', s=f'{width}x{height}', r=fps)
            .output('pipe:1', format='mp4', vcodec='libx264', crf=23, preset='fast')
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
        )

        def write_frames(frames):
            for frame in frames:
                combined = blend_images(background, frame)
                frame_rgb = np.array(combined.convert("RGB"))
                process.stdin.write(frame_rgb.tobytes())

        write_frames(intro_frames)
        write_frames(main_frames)

        process.stdin.close()
        output_buffer.write(process.stdout.read())
        process.wait()

        if process.returncode != 0:
            return JsonResponse({"error": "FFmpeg processing failed"}, status=500)

        output_buffer.seek(0)

        return StreamingHttpResponse(output_buffer, content_type="video/mp4")
