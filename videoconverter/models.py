import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

# Определение состояний задачи согласно UML диаграмме
class JobState(Enum):
    QUEUED = "В очереди"
    RUNNING = "В процессе"
    PAUSED = "Пауза"
    DONE = "Завершено"
    FAILED = "Ошибка"

@dataclass
class FormatProfile:
    """
    Профиль настроек конвертации.
    Поля соответствуют макету окна настроек.
    """
    format: str = "mp4"
    video_codec: str = "h264"
    audio_codec: str = "aac"
    resolution: str = "1920x1080"
    bitrate: str = "4M"
    fps: int = 30

@dataclass
class Job:
    """
    Класс задачи на конвертацию.
    Соответствует сущности Job из UML.
    """
    source_path: Path
    output_dir: Path
    profile: FormatProfile
    id: UUID = field(default_factory=uuid4)
    state: JobState = JobState.QUEUED
    progress: int = 0
    error_message: Optional[str] = None

    @property
    def output_filename(self) -> Path:
        """Генерирует имя выходного файла."""
        new_name = f"{self.source_path.stem}.{self.profile.format.lower()}"
        return self.output_dir / new_name

@dataclass
class Settings:
    """
    Класс для хранения и сохранения настроек приложения.
    Реализует требования к сохранению параметров[cite: 161].
    """
    output_path: str = str(Path.home() / "Videos")
    hot_folder_enabled: bool = False
    hot_folder_path: str = ""
    notifications_enabled: bool = False
    default_profile: FormatProfile = field(default_factory=FormatProfile)

    SETTINGS_FILE = Path("settings.json")

    @classmethod
    def load(cls) -> "Settings":
        if not cls.SETTINGS_FILE.exists():
            return cls()
        try:
            with open(cls.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Восстанавливаем вложенный объект FormatProfile
                profile_data = data.pop("default_profile", {})
                settings = cls(**data)
                settings.default_profile = FormatProfile(**profile_data)
                return settings
        except Exception as e:
            print(f"[ERROR] Не удалось загрузить настройки: {e}")
            return cls()

    def save(self) -> None:
        try:
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Не удалось сохранить настройки: {e}")