import pytest
from pathlib import Path
from videoconverter.converter import build_ffmpeg_command, ConversionOptions, ConversionError, convert_file
from videoconverter.cli import _validate_bitrate, _build_parser


# --- ТЕСТ 1: Проверка логики (Unit-тест) ---
def test_build_ffmpeg_command():
    """Проверяет, что команда для FFmpeg собирается правильно."""
    options = ConversionOptions(
        target_format="mp4",
        output_dir=Path("out"),
        video_bitrate="2M",
        resolution="1920x1080"
    )
    input_file = Path("video.avi")
    output_file = Path("out/video.mp4")

    cmd = build_ffmpeg_command(input_file, output_file, options)

    # Проверяем наличие ключевых флагов в списке
    assert "ffmpeg" in cmd
    assert "-y" in cmd
    assert str(input_file) in cmd
    assert str(output_file) in cmd
    # Проверяем, что опции применились
    assert "-b:v" in cmd
    assert "2M" in cmd
    assert "-s" in cmd
    assert "1920x1080" in cmd


# --- ТЕСТ 2: Параметризованный тест (валидация) ---
@pytest.mark.parametrize("input_val, expected", [
    ("800k", "800k"),  # Корректный ввод
    ("2M", "2M"),  # Корректный ввод
    ("  192k  ", "192k"),  # Пробелы должны обрезаться
    ("invalid", None),  # Некорректный ввод
    ("100", "100"),  # Нет суффикса k/M
    (None, None),  # Пустой ввод
])
def test_validate_bitrate(input_val, expected):
    """Проверяет работу валидатора битрейта на разных данных."""
    result = _validate_bitrate("test", input_val)
    assert result == expected


# --- ТЕСТ 3: Негативный тест (обработка ошибок) ---
def test_convert_missing_file():
    """Проверяет, что программа выбрасывает ошибку, если файла нет."""
    options = ConversionOptions(target_format="mp4", output_dir=Path("out"))
    fake_file = Path("ghost_file.mkv")

    # Ожидаем, что вызов функции поднимет исключение ConversionError
    with pytest.raises(ConversionError) as excinfo:
        convert_file(fake_file, options)

    assert "Файл не найден" in str(excinfo.value)

# --- ТЕСТ 4: Тест парсера аргументов (CLI) ---
def test_cli_parser_defaults():
    parser = _build_parser()
    # Эмулируем ввод команды в терминале:
    # python main.py my_video.avi -f mkv
    args = parser.parse_args(["my_video.avi", "-f", "mkv"])
    # Проверяем, что формат считался верно
    assert args.format == "mkv"
    # Проверяем, что входной файл попал в список
    assert args.inputs == ["my_video.avi"]
    assert args.output_dir == "output"