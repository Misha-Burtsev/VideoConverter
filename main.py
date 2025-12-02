import sys
import shutil
from videoconverter.cli import main as cli_main
# Импортируем функцию запуска GUI (мы её добавим сейчас в __init__ или вызовем напрямую)
from videoconverter.gui import run_gui


def ensure_ffmpeg_installed() -> None:
    if shutil.which("ffmpeg") is None:
        print("[ERROR] Утилита 'ffmpeg' не найдена в системе.")
        sys.exit(1)


if __name__ == "__main__":
    ensure_ffmpeg_installed()

    # Если переданы аргументы (например: main.py video.mp4 -f mkv), запускаем CLI
    if len(sys.argv) > 1:
        cli_main()
    else:
        # Иначе запускаем графический интерфейс
        run_gui()