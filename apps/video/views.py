import os
import cv2
import numpy as np
import subprocess
from PIL import Image
from django.http import FileResponse
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
            logger.error("Файл background не передан.")
            return Response({"error": "Background image is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            background = Image.open(request.FILES['background']).convert("RGBA")
            width, height = background.size
            fps = int(request.data.get("fps", 30))
            logger.info(f"Background загружен: {width}x{height}, FPS: {fps}")
        except Exception as e:
            logger.error(f"Ошибка при обработке background: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        base_path = "/home/platon/mult/data_for_video"
        intro_folder = os.path.join(base_path, "intro")
        main_folder = os.path.join(base_path, "main")
        audio_path = os.path.join(base_path, "audio.wav")
        temp_video_path = "temp_video.mp4"
        final_video_path = "output_video.mp4"

        for folder in [intro_folder, main_folder]:
            if not os.path.exists(folder) or not os.path.isdir(folder):
                logger.warning(f"Папка {folder} не найдена или не является директорией.")

        if not os.path.exists(audio_path):
            logger.warning(f"Аудиофайл {audio_path} отсутствует.")

        intro_frames = self.load_images_from_folder(intro_folder)
        main_frames = self.load_images_from_folder(main_folder)

        if not intro_frames and not main_frames:
            logger.error("Нет кадров для обработки.")
            return Response({"error": "No frames to process"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))

            self.write_frames(video, background, intro_frames)
            self.write_frames(video, background, main_frames)

            video.release()
            logger.info(f"Видео сохранено: {temp_video_path}")
        except Exception as e:
            logger.error(f"Ошибка при создании видео: {e}")
            return Response({"error": "Failed to generate video"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            if os.path.exists(audio_path):
                logger.info("Добавление аудио в видео...")
                command = [
                    FFMPEG_PATH, "-y", "-i", temp_video_path, "-i", audio_path,
                    "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", final_video_path
                ]
                subprocess.run(command, check=True)
                logger.info(f"Финальное видео сохранено: {final_video_path}")
            else:
                os.rename(temp_video_path, final_video_path)
                logger.info("Аудиофайл отсутствует, видео сохранено без звука.")
        except Exception as e:
            logger.error(f"Ошибка при добавлении звука: {e}")
            return Response({"error": "Failed to add audio"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not os.path.exists(final_video_path):
            logger.error(f"Файл {final_video_path} не найден после рендеринга.")
            return Response({"error": "Video file not found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return FileResponse(open(final_video_path, "rb"), as_attachment=True, filename="generated_video.mp4")

    def load_images_from_folder(self, folder):
        if not os.path.exists(folder):
            logger.warning(f"Папка {folder} не найдена.")
            return []

        images = []
        for filename in sorted(os.listdir(folder)):
            if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                try:
                    img_path = os.path.join(folder, filename)
                    img = Image.open(img_path).convert("RGBA")
                    images.append(img)
                except Exception as e:
                    logger.error(f"Ошибка загрузки изображения {filename}: {e}")

        logger.info(f"Загружено {len(images)} изображений из {folder}")
        return images

    def write_frames(self, video, background, frames):
        if not frames:
            logger.warning("Попытка добавить пустой список кадров.")
            return

        for img in frames:
            img = Image.alpha_composite(background, img).convert("RGB")
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            video.write(frame)
