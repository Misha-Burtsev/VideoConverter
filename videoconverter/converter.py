import subprocess
import re
import sys
import time
import threading
import psutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Callable, Iterable

# Регулярные выражения для чтения вывода FFmpeg (нужны для прогресс-бара)
DURATION_REGEX = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})")
TIME_REGEX = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")


@dataclass
class ConversionOptions:
    target_format: str
    output_dir: Path
    video_bitrate: Optional[str] = None
    audio_bitrate: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None


class ConversionError(Exception):
    pass


def build_ffmpeg_command(
        input_file: Path,
        output_file: Path,
        options: ConversionOptions,
) -> List[str]:
    cmd: List[str] = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),
    ]

    if options.video_bitrate:
        cmd.extend(["-b:v", options.video_bitrate])

    if options.audio_bitrate:
        cmd.extend(["-b:a", options.audio_bitrate])

    if options.resolution:
        cmd.extend(["-s", options.resolution])

    if options.fps:
        cmd.extend(["-r", str(options.fps)])

    cmd.append(str(output_file))
    return cmd


def get_video_duration(input_file: Path) -> float:
    cmd = ["ffmpeg", "-i", str(input_file)]
    try:
        # Запускаем ffmpeg просто чтобы считать метаданные из stderr
        result = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        match = DURATION_REGEX.search(result.stderr)
        if match:
            hours, mins, secs, centis = map(int, match.groups())
            return hours * 3600 + mins * 60 + secs + centis / 100.0
    except Exception:
        pass
    return 1.0  # Возвращаем 1, чтобы избежать деления на ноль


def convert_file(
        input_file: Path,
        options: ConversionOptions,
        progress_callback: Optional[Callable[[int], None]] = None,
        pause_event: Optional[threading.Event] = None,
        stop_event: Optional[threading.Event] = None
) -> None:
    if not input_file.exists():
        raise ConversionError(f"Файл не найден: {input_file}")

    output_name = f"{input_file.stem}.{options.target_format.lstrip('.')}"
    output_file = options.output_dir / output_name
    cmd = build_ffmpeg_command(input_file, output_file, options)
    total_duration = get_video_duration(input_file)

    print(f"[INFO] Конвертация: {input_file} -> {output_file}")

    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    process = None
    is_paused = False  # Флаг для отслеживания текущего состояния

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace', creationflags=creationflags
        )

        # Получаем объект процесса psutil для управления (пауза/продолжение)
        p = psutil.Process(process.pid)

        while True:
            # 1. СТОП
            if stop_event and stop_event.is_set():
                if is_paused: p.resume()  # Если был на паузе, надо "разбудить", чтобы убить
                process.terminate()
                raise ConversionError("STOPPED")

            # 2. ПАУЗА (СИСТЕМНАЯ)
            if pause_event and pause_event.is_set():
                if not is_paused:
                    # Ставим процесс на системную паузу
                    p.suspend()
                    is_paused = True

                time.sleep(0.2)  # Просто ждем, пока флаг не снимут
                continue
            else:
                # Если флаг сняли, а процесс все еще спит — будим
                if is_paused:
                    p.resume()
                    is_paused = False

            # Читаем вывод (только если не на паузе)
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break

            if line and progress_callback:
                match = TIME_REGEX.search(line)
                if match:
                    h, m, s, cs = map(int, match.groups())
                    current_seconds = h * 3600 + m * 60 + s + cs / 100.0
                    percent = int((current_seconds / total_duration) * 100)
                    progress_callback(min(percent, 99))

        if process.returncode != 0:
            # Обработка ситуаций, когда процесс убили внешне
            if stop_event and stop_event.is_set():
                raise ConversionError("STOPPED")
            raise ConversionError(f"Ошибка FFmpeg (код {process.returncode})")

        if progress_callback and not (stop_event and stop_event.is_set()):
            progress_callback(100)
            print(f"[OK] Готово: {output_file}")

    except OSError as exc:
        raise ConversionError(f"Не удалось запустить ffmpeg: {exc}") from exc
    finally:
        if process and process.poll() is None:
            # На всякий случай
            try:
                process.terminate()
            except:
                pass


# convert_files для CLI оставляем без изменений
def convert_files(inputs: Iterable[Path], options: ConversionOptions) -> None:
    for input_file in inputs:
        try:
            convert_file(input_file, options)
        except ConversionError as exc:
            print(f"[ERROR] {exc}")