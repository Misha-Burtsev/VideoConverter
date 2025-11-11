import argparse
from pathlib import Path

from .converter import ConversionOptions, convert_files

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


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    options = ConversionOptions(
        target_format=args.format,
        output_dir=output_dir,
        video_bitrate=args.video_bitrate,
        audio_bitrate=args.audio_bitrate,
        resolution=args.resolution,
    )

    print("[INFO] Запуск конвертации")
    print(f"[INFO] Целевой формат: {options.target_format}")
    print(f"[INFO] Директория вывода: {options.output_dir}")

    convert_files(input_paths, options)