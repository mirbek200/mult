import os
import cv2
import numpy as np
import subprocess
from PIL import Image
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

FFMPEG_PATH = "/usr/bin/ffmpeg"

class VideoGenerationView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        logger.info("Запрос на генерацию видео получен.")

        if 'background' not in request.FILES:
            return Response({"error": "Background image is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            background = Image.open(request.FILES['background']).convert("RGBA")
            width, height = background.size
            fps = int(request.data.get("fps", 30))
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



        if not intro_frames and not main_frames:
            return Response({"error": "No frames to process"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))

        self.write_frames(video, background, intro_frames)
        self.write_frames(video, background, main_frames)
        video.release()

        if os.path.exists(audio_path):
            subprocess.run(command, check=True)
        else:
            os.rename(temp_video_path, final_video_path)


            img = Image.alpha_composite(background, img).convert("RGB")
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            video.write(frame)
