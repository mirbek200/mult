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


import logging

logger = logging.getLogger(__name__)

class VideoGenerationView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        logger.info("Запрос получен")

        if 'background' not in request.FILES:
            logger.error("Файл background не передан")
            return Response({"error": "Background image is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            background = Image.open(request.FILES['background']).convert("RGBA")
            width, height = background.size
            fps = int(request.data.get("fps", 30))
            logger.info(f"Background image загружен: {width}x{height}, FPS: {fps}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке background: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Проверяем существование директорий
        intro_folder = "/home/ubuntu/mult/data_for_video/intro"
        main_folder = "/home/ubuntu/mult/data_for_video/main"
        audio_path = "/home/ubuntu/mult/data_for_video/audio.wav"

        for folder in [intro_folder, main_folder]:
            if not os.path.exists(folder):
                logger.error(f"Папка {folder} не найдена")

        if not os.path.exists(audio_path):
            logger.warning(f"Аудиофайл {audio_path} отсутствует")

        # Загружаем изображения
        intro_frames = self.load_images_from_folder(intro_folder)
        main_frames = self.load_images_from_folder(main_folder)

        if not intro_frames and not main_frames:
            logger.error("Нет кадров для обработки!")
            return Response({"error": "No frames to process"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Создаём видео
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            output_path = "output_video.mp4"
            video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            self.write_frames(video, background, intro_frames)
            self.write_frames(video, background, main_frames)
            video.release()
            logger.info(f"Видео сохранено в {output_path}")
        except Exception as e:
            logger.error(f"Ошибка при создании видео: {e}")
            return Response({"error": "Failed to generate video"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return FileResponse(open(output_path, "rb"), as_attachment=True, filename="generated_video.mp4")

