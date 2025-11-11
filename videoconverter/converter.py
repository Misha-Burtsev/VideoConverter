import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class ConversionOptions:
    # параметры конвертации видео.
    target_format: str
    output_dir: Path
    video_bitrate: Optional[str] = None
    audio_bitrate: Optional[str] = None
    resolution: Optional[str] = None


class ConversionError(Exception):
    # ошибка при конвертации видеофайла.
    pass


def build_ffmpeg_command(
    input_file: Path,
    output_file: Path,
    options: ConversionOptions,
) -> List[str]:
    # формирует команду ffmpeg для конвертации одного файла.
    cmd: List[str] = [
        "ffmpeg",
        "-y",              # перезаписывать существующий файл
        "-i", str(input_file), # указывает, что следующий аргумент — это входной файл
    ]

    # если options.video_bitrate не None, она добавляет "-b:v"(флаг битрейта видео) и само значение битрейта
    if options.video_bitrate:
        cmd.extend(["-b:v", options.video_bitrate])

    if options.audio_bitrate:
        cmd.extend(["-b:a", options.audio_bitrate])

    if options.resolution:
        cmd.extend(["-s", options.resolution])

    # выходной файл, добавляется путь
    cmd.append(str(output_file))
    return cmd


def convert_file(input_file: Path, options: ConversionOptions) -> None:     # конвертирует один файл с заданными параметрами.
    if not input_file.exists():
        raise ConversionError(f"Файл не найден: {input_file}")

    # input_file.stem берет имя файла без расширения
    # options.target_format.lstrip('.') убирает точку из ".mp4"
    output_name = f"{input_file.stem}.{options.target_format.lstrip('.')}"
    # с помощью pathlib "склеивает" папку вывода и новое имя файла
    output_file = options.output_dir / output_name

    cmd = build_ffmpeg_command(input_file, output_file, options) # сборка команды для ffmpeg

    print(f"[INFO] Конвертация: {input_file} -> {output_file}")
    print(f"[DEBUG] Команда: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc: # ловит ошибку, если ffmpeg вообще не найден в системе
        # ffmpeg не найден или не запускается
        raise ConversionError(f"Не удалось запустить ffmpeg: {exc}") from exc

    if result.returncode != 0:
        # выводим stderr для диагностики
        raise ConversionError(
            f"ffmpeg завершился с ошибкой для файла {input_file}\n"
            f"Код возврата: {result.returncode}\n"
            f"stderr:\n{result.stderr}"
        )

    print(f"[OK] Готово: {output_file}")


def convert_files(
    inputs: Iterable[Path],
    options: ConversionOptions,
) -> None:
    """
    Конвертирует несколько файлов подряд.
    Ошибки по отдельным файлам не прерывают обработку остальных.
    """
    for input_file in inputs:
        try:
            convert_file(input_file, options)
        except ConversionError as exc:
            print(f"[ERROR] {exc}")
