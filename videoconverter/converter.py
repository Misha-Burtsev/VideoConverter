import subprocess
import re
import sys
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
    fps: Optional[int] = None  # Добавил FPS, так как он есть в твоем макете GUI


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
    """
    Новая функция: узнает длительность видео в секундах.
    Нужна, чтобы рисовать полоску прогресса (вычислять %).
    """
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
        progress_callback: Optional[Callable[[int], None]] = None
) -> None:
    if not input_file.exists():
        raise ConversionError(f"Файл не найден: {input_file}")

    output_name = f"{input_file.stem}.{options.target_format.lstrip('.')}"
    output_file = options.output_dir / output_name

    cmd = build_ffmpeg_command(input_file, output_file, options)

    # Получаем длительность для расчета процентов
    total_duration = get_video_duration(input_file)

    print(f"[INFO] Конвертация: {input_file} -> {output_file}")

    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # FFmpeg пишет статус в stderr
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags
        )

        # Читаем вывод построчно
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break

            if line and progress_callback:
                # Ищем "time=00:00:05.12" в строке лога
                match = TIME_REGEX.search(line)
                if match:
                    h, m, s, cs = map(int, match.groups())
                    current_seconds = h * 3600 + m * 60 + s + cs / 100.0
                    percent = int((current_seconds / total_duration) * 100)
                    progress_callback(min(percent, 99))  # Обновляем GUI

        if process.returncode != 0:
            raise ConversionError(f"Ошибка FFmpeg (код {process.returncode})")

        if progress_callback:
            progress_callback(100)

        print(f"[OK] Готово: {output_file}")

    except OSError as exc:
        raise ConversionError(f"Не удалось запустить ffmpeg: {exc}") from exc