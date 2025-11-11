
import shutil
import sys

from videoconverter.cli import main as cli_main


def ensure_ffmpeg_installed() -> None:
    """
    Проверяет, что ffmpeg доступен в PATH.
    Если нет — выводит понятное сообщение и завершает программу.
    """
    if shutil.which("ffmpeg") is None:
        print("[ERROR] Утилита 'ffmpeg' не найдена в системе.")
        print("Установите ffmpeg и убедитесь, что она доступна в PATH.")
        print("Пример для Debian/Ubuntu: sudo apt install ffmpeg")
        sys.exit(1)


if __name__ == "__main__":
    ensure_ffmpeg_installed()
    cli_main()