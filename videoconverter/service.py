import threading
import time
from typing import List, Optional
from uuid import UUID

from .models import Job, JobState, Settings
from .converter import convert_file, ConversionOptions, ConversionError


class ConverterService:
    def __init__(self):
        self.queue: List[Job] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def add_job(self, job: Job) -> None:
        """Добавляет задачу в конец очереди."""
        self.queue.append(job)

    def remove_job(self, job_id: UUID) -> None:
        """Удаляет задачу из очереди (если она не в процессе выполнения)."""
        # Оставляем только те задачи, у которых ID не совпадает
        self.queue = [j for j in self.queue if j.id != job_id]

    def clear_queue(self) -> None:
        """Очищает список задач, кроме текущей выполняемой."""
        self.queue = [j for j in self.queue if j.state == JobState.RUNNING]

    def start_processing(self) -> None:
        """Запускает фоновый поток обработки."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop_processing(self) -> None:
        """Останавливает обработку (после завершения текущей задачи)."""
        self._running = False
        self._stop_event.set()

    def _worker(self) -> None:
        """Основной цикл, который крутится в отдельном потоке."""
        while self._running:
            # 1. Ищем следующую задачу со статусом QUEUED
            # next() вернет первую найденную или None
            job = next((j for j in self.queue if j.state == JobState.QUEUED), None)

            if not job:
                # Если задач нет, спим 1 секунду и проверяем снова
                time.sleep(1)
                continue

            # 2. Меняем статус на "В процессе"
            job.state = JobState.RUNNING
            job.progress = 0

            try:
                # 3. Подготавливаем параметры для твоего конвертера
                # Маппинг: Job.FormatProfile -> converter.ConversionOptions

                # Создаем папку вывода, если ее нет
                job.output_dir.mkdir(parents=True, exist_ok=True)

                options = ConversionOptions(
                    target_format=job.profile.format,
                    output_dir=job.output_dir,
                    video_bitrate=job.profile.bitrate,  # Используем общий битрейт для видео
                    resolution=job.profile.resolution,
                    fps=job.profile.fps
                    # audio_bitrate пока не задаем, оставим по умолчанию ffmpeg
                )

                # Функция, которую convert_file будет дергать для обновления процентов
                def update_progress(p: int):
                    job.progress = p

                # 4. Запускаем конвертацию
                convert_file(job.source_path, options, progress_callback=update_progress)

                # Если функция завершилась без исключений — успех
                job.state = JobState.DONE
                job.progress = 100

            except Exception as e:
                # Если что-то упало — сохраняем ошибку
                print(f"[SERVICE ERROR] {e}")
                job.state = JobState.FAILED
                job.error_message = str(e)

            # Проверка, не попросили ли нас остановиться
            if self._stop_event.is_set():
                break

        self._running = False