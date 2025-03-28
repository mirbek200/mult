import os
import cv2
import numpy as np
import subprocess
import boto3
from PIL import Image
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

FFMPEG_PATH = "/usr/bin/ffmpeg"

# Конфигурация S3
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = "my-video-bucket"
AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url=AWS_S3_ENDPOINT_URL,
)

temp_dir = "/tmp/video_processing"
os.makedirs(temp_dir, exist_ok=True)

def download_file_from_s3(s3_path, local_path):
    try:
        s3_client.download_file(AWS_STORAGE_BUCKET_NAME, s3_path, local_path)
        logger.info(f"Файл {s3_path} загружен в {local_path}")
    except Exception as e:
        logger.error(f"Ошибка загрузки {s3_path}: {e}")

def load_images_from_s3(folder_prefix, local_folder):
    os.makedirs(local_folder, exist_ok=True)
    images = []
    try:
        response = s3_client.list_objects_v2(Bucket=AWS_STORAGE_BUCKET_NAME, Prefix=folder_prefix)
        if 'Contents' in response:
            for obj in response['Contents']:
                filename = os.path.basename(obj['Key'])
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    local_path = os.path.join(local_folder, filename)
                    download_file_from_s3(obj['Key'], local_path)
                    images.append(local_path)
        return images
    except Exception as e:
        logger.error(f"Ошибка загрузки изображений из {folder_prefix}: {e}")
        return []

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

        intro_folder = os.path.join(temp_dir, "intro")
        main_folder = os.path.join(temp_dir, "main")
        audio_path = os.path.join(temp_dir, "audio.wav")

        intro_frames = load_images_from_s3("intro/", intro_folder)
        main_frames = load_images_from_s3("main/", main_folder)
        download_file_from_s3("audio.wav", audio_path)

        if not intro_frames and not main_frames:
            return Response({"error": "No frames to process"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        temp_video_path = os.path.join(temp_dir, "temp_video.mp4")
        final_video_path = os.path.join(temp_dir, "output_video.mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))

        self.write_frames(video, background, intro_frames)
        self.write_frames(video, background, main_frames)
        video.release()

        if os.path.exists(audio_path):
            command = [FFMPEG_PATH, "-y", "-i", temp_video_path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", final_video_path]
            subprocess.run(command, check=True)
        else:
            os.rename(temp_video_path, final_video_path)

        s3_video_path = "videos/generated_video.mp4"
        s3_client.upload_file(final_video_path, AWS_STORAGE_BUCKET_NAME, s3_video_path)
        video_url = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/{s3_video_path}"
        return JsonResponse({"video_url": video_url}, status=status.HTTP_200_OK)

    def write_frames(self, video, background, frame_paths):
        for frame_path in frame_paths:
            img = Image.open(frame_path).convert("RGBA")
            img = Image.alpha_composite(background, img).convert("RGB")
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            video.write(frame)
