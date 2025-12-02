import threading
import time
import os
from pathlib import Path
from typing import List, Optional, Set
from uuid import UUID

from .models import Job, JobState, Settings
from .converter import convert_file, ConversionOptions, ConversionError

# Список поддерживаемых расширений для горячей папки
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}


class ConverterService:
    def __init__(self):
        self.queue: List[Job] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        # ДЛЯ ГОРЯЧЕЙ ПАПКИ
        self._processed_files: Set[Path] = set()  # Запоминаем, что уже добавили
        self._watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._watcher_thread.start()

    def add_job(self, job: Job) -> None:
        self.queue.append(job)

    def remove_job(self, job_id: UUID) -> None:
        job_to_remove = next((j for j in self.queue if j.id == job_id), None)
        if job_to_remove:
            self._processed_files.discard(job_to_remove.source_path)

        self.queue = [j for j in self.queue if j.id != job_id]

    def clear_queue(self) -> None:
        jobs_to_remove = [j for j in self.queue if j.state != JobState.RUNNING]

        for job in jobs_to_remove:
            self._processed_files.discard(job.source_path)

        self.queue = [j for j in self.queue if j.state == JobState.RUNNING]

    def has_pending_jobs(self) -> bool:
        return any(j.state == JobState.QUEUED for j in self.queue)

    def start_processing(self) -> None:
        if self._running: return
        self._running = True
        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop_processing(self) -> None:
        self._running = False
        self._pause_event.clear()
        self._stop_event.set()

    def pause_processing(self) -> None:
        self._pause_event.set()

    def resume_processing(self) -> None:
        self._pause_event.clear()

    # === ЛОГИКА ГОРЯЧЕЙ ПАПКИ ===
    def _is_file_ready(self, path: Path) -> bool:
        """
        Проверяет, завершилась ли запись файла (стабилен ли размер).
        Нужно, чтобы не начать конвертировать файл, который еще копируется.
        """
        try:
            size1 = path.stat().st_size
            time.sleep(1)  # Ждем секунду
            size2 = path.stat().st_size
            return size1 == size2 and size1 > 0
        except OSError:
            return False

    def _watcher_loop(self):
        """Бесконечный цикл проверки горячей папки."""
        while True:
            try:
                settings = Settings.load()

                if settings.hot_folder_enabled and settings.hot_folder_path:
                    folder = Path(settings.hot_folder_path)

                    if folder.exists() and folder.is_dir():
                        # Сканируем файлы
                        for file_path in folder.iterdir():
                            if (file_path.suffix.lower() in VIDEO_EXTENSIONS
                                    and file_path not in self._processed_files):

                                already_in_queue = any(j.source_path == file_path for j in self.queue)

                                if not already_in_queue and self._is_file_ready(file_path):
                                    new_job = Job(
                                        source_path=file_path,
                                        output_dir=Path(settings.output_path),
                                        profile=settings.default_profile
                                    )
                                    self.add_job(new_job)
                                    self._processed_files.add(file_path)
                                    print(f"[HOT FOLDER] Обнаружен новый файл: {file_path.name}")

                                    # === АВТОМАТИЧЕСКИЙ ЗАПУСК ===
                                    if not self._running:
                                        self.start_processing()
                                    # =============================
                    else:
                        pass

            except Exception as e:
                print(f"[WATCHER ERROR] {e}")

            time.sleep(3)

    # ОСНОВНОЙ РАБОЧИЙ ПОТОК
    def _worker(self) -> None:
        while self._running:
            if self._pause_event.is_set():
                time.sleep(0.5)
                continue

            job = next((j for j in self.queue if j.state == JobState.QUEUED), None)

            if not job:
                self._running = False
                break

            job.state = JobState.RUNNING
            job.progress = 0

            try:
                job.output_dir.mkdir(parents=True, exist_ok=True)
                options = ConversionOptions(
                    target_format=job.profile.format,
                    output_dir=job.output_dir,
                    video_bitrate=job.profile.bitrate,
                    resolution=job.profile.resolution,
                    fps=job.profile.fps
                )

                def update_progress(p: int):
                    job.progress = p

                convert_file(
                    job.source_path,
                    options,
                    progress_callback=update_progress,
                    pause_event=self._pause_event,
                    stop_event=self._stop_event
                )

                job.state = JobState.DONE
                job.progress = 100

            except ConversionError as e:
                if str(e) == "STOPPED":
                    job.state = JobState.CANCELLED
                    print(f"[INFO] Задача отменена пользователем: {job.source_path.name}")
                else:
                    print(f"[SERVICE ERROR] {e}")
                    job.state = JobState.FAILED
                    job.error_message = str(e)
            except Exception as e:
                print(f"[CRITICAL ERROR] {e}")
                job.state = JobState.FAILED
                job.error_message = str(e)

            if self._stop_event.is_set():
                break

        self._running = False