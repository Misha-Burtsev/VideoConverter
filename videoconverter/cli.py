import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="videoconverter",
        description="Заготовка CLI для проекта VideoConverter"
    )

    parser.add_argument(
        "inputs",
        nargs="*",                              # Принимать ноль или больше аргументов. Все эти аргументы будут собраны в список (list).
        help="Пути к исходным видеофайлам"
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args() # Список из того, что ввел пользователь

    if not args.inputs:
        print("VideoConverter: файлы не указаны.")
        print("Пример запуска: python main.py video1.mp4 video2.avi")
        return

    files = [Path(p) for p in args.inputs]

    print("VideoConverter: получены пути к файлам:")
    for f in files:
        print(f"  - {f}")