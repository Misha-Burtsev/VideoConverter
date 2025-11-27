import argparse
import re
from pathlib import Path

from .converter import ConversionOptions, convert_file

# допустимые форматы выходного видео
VALID_FORMATS = {"mp4", "avi", "mkv", "mov", "wmv"}

# простой шаблон для битрейта: число + опционально k или M (например, 800k, 2M)
BITRATE_PATTERN = re.compile(r"^\d+[kKmM]?$")

# шаблон для разрешения вида 1920x1080
RESOLUTION_PATTERN = re.compile(r"^\d+x\d+$")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="videoconverter",
        description="Конвертер видеофайлов на базе FFmpeg (CLI)"
    )

    parser.add_argument(
        "inputs",
        nargs="+",                      # один или больше аргументов
        help="Пути к исходным видеофайлам"
    )

    parser.add_argument(
        "-f", "--format",
        required=True,                  # программа откажется запускаться, если пользователь не укажет, в какой формат он хочет конвертировать.
        help="Целевой формат видео (например, mp4, avi, mkv)"
    )

    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default="output",
        help="Директория для сохранения сконвертированных файлов (по умолчанию: ./output)"
    )

    parser.add_argument(
        "--video-bitrate",
        type=str,
        help="Битрейт видео, например 2M, 800k"
    )

    parser.add_argument(
        "--audio-bitrate",
        type=str,
        help="Битрейт аудио, например 192k"
    )

    parser.add_argument(
        "--resolution",
        type=str,
        help="Разрешение выходного видео, например 1920x1080"
    )

    return parser


def _validate_bitrate(label: str, value: str | None) -> str | None:
    """
    Проверка формата битрейта.
    Возвращает нормализованное значение (обрезанные пробелы) или None.
    """
    if value is None:
        return None

    normalized = value.strip()
    if not BITRATE_PATTERN.fullmatch(normalized):
        print(
            f"[ERROR] Неверный {label} битрейт: '{value}'. "
            "Ожидается целое число и опционально суффикс k или M, например 800k или 2M."
        )
        return None

    return normalized


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # нормализуем формат
    target_format = args.format.lower()

    if target_format not in VALID_FORMATS:
        print(
            f"[ERROR] Неверный формат: '{args.format}'. "
            f"Допустимые: {', '.join(sorted(VALID_FORMATS))}"
        )
        return

    # нормализуем разрешение и проверяем формат
    resolution = None
    if args.resolution:
        # пользователь может случайно добавить пробелы, убираем их по краям
        normalized_res = args.resolution.strip()
        if not RESOLUTION_PATTERN.fullmatch(normalized_res):
            print(
                f"[ERROR] Неверный формат разрешения: '{args.resolution}'. "
                "Ожидается вид WIDTHxHEIGHT (например, 1920x1080)."
            )
            return
        resolution = normalized_res

    # проверка битрейтов
    video_bitrate = _validate_bitrate("видео", args.video_bitrate)
    if args.video_bitrate is not None and video_bitrate is None:
        # была ошибка формата битрейта видео
        return

    audio_bitrate = _validate_bitrate("аудио", args.audio_bitrate)
    if args.audio_bitrate is not None and audio_bitrate is None:
        # была ошибка формата битрейта аудио
        return

    input_paths = [Path(p) for p in args.inputs]

    # разделяем существующие и несуществующие файлы
    existing_files = [p for p in input_paths if p.exists()]
    missing_files = [p for p in input_paths if not p.exists()]

    if missing_files:
        print("[WARN] Следующие файлы не найдены и будут пропущены:")
        for p in missing_files:
            print(f"  - {p}")

    if not existing_files:
        print("[ERROR] Ни один из указанных файлов не найден. Конвертация прервана.")
        return

    output_dir = Path(args.output_dir)

    # пробуем создать директорию вывода
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[ERROR] Не удалось создать директорию вывода '{output_dir}': {exc}")
        return

    options = ConversionOptions(
        target_format=target_format,
        output_dir=output_dir,
        video_bitrate=video_bitrate,
        audio_bitrate=audio_bitrate,
        resolution=resolution,
    )

    print("[INFO] Запуск конвертации")
    print(f"[INFO] Целевой формат: {options.target_format}")
    print(f"[INFO] Директория вывода: {options.output_dir}")
    print(f"[INFO] Файлов к обработке: {len(existing_files)}")

    convert_file(existing_files, options)
