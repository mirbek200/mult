import os
import cv2
import numpy as np
from PIL import Image, ImageOps
from django.http import FileResponse, JsonResponse
from moviepy import VideoFileClip, AudioFileClip
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

        # intro_folder = "data_for_video/intro"
        # main_folder = "data_for_video/main"
        # audio_path = "data_for_video/audio.wav"

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        intro_folder = os.path.join(BASE_DIR, "data_for_video/intro")
        main_folder = os.path.join(BASE_DIR, "data_for_video/main")
        audio_path = os.path.join(BASE_DIR, "data_for_video/audio.wav")


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

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        output_path = "output_video.mp4"
        video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        def write_frames(frames):
            for frame in frames:
                combined = blend_images(background, frame)
                frame_bgr = cv2.cvtColor(np.array(combined.convert("RGB")), cv2.COLOR_RGB2BGR)
                video.write(frame_bgr)

        write_frames(intro_frames)
        write_frames(main_frames)
        video.release()

        if os.path.exists(audio_path):
            video_clip = VideoFileClip(output_path)
            audio_clip = AudioFileClip(audio_path)
            video_clip = video_clip.with_audio(audio_clip)
            output_with_audio = "final_output.mp4"
            video_clip.write_videofile(output_with_audio, codec="libx264", fps=fps)
            os.remove(output_path)  # Удаляем файл без звука
            output_path = output_with_audio

        if not os.path.exists(output_path):
            return JsonResponse({"error": "Failed to generate video"}, status=500)

        return FileResponse(
            open(output_path, "rb"),
            as_attachment=True,
            filename="generated_video.mp4",
            content_type="video/mp4"
        )
