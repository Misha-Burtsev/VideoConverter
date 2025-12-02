import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path

from .models import Job, JobState, Settings
from .service import ConverterService
from .settings_window import SettingsWindow, CustomPopup


class MainWindow(ttk.Window):
    def __init__(self, service: ConverterService):
        super().__init__(themename="litera")
        self.service = service
        self.title("VideoConverter")
        self.geometry("800x650")

        self._processing_started = False
        self.font_header = ("Helvetica", 18, "bold")
        self.font_ui = ("Helvetica", 10)

        self._init_ui()
        self._update_loop()

    def _init_ui(self):
        # Используем стандартный tk.Frame, так как он позволяет легко задать цвет рамки
        wrapper = tk.Frame(self, highlightbackground="black", highlightthickness=1, borderwidth=0)
        wrapper.pack(fill=tk.BOTH, expand=True)  # Растягиваем на всё окно

        # Теперь основной контейнер кладем ВНУТРЬ wrapper, а не self
        main_container = ttk.Frame(wrapper, padding=15)
        main_container.pack(fill=BOTH, expand=True)

        # 1. Панель управления
        controls_frame = ttk.Frame(main_container)
        controls_frame.pack(fill=X, pady=(0, 15))

        # Левые кнопки
        btn_add = ttk.Button(controls_frame, text="Добавить файлы...", bootstyle="outline", command=self._add_files)
        btn_add.pack(side=LEFT, padx=(0, 5))

        # Загружаем текущий формат из настроек для отображения по умолчанию
        current_fmt = Settings.load().default_profile.format.upper()

        self.var_quick_format = tk.StringVar(value=current_fmt)
        self.combo_quick_fmt = ttk.Combobox(
            controls_frame,
            textvariable=self.var_quick_format,
            values=['MP4', 'AVI', 'MKV', 'MOV', 'WMV'],
            state="readonly",
            width=6,
            bootstyle="primary"  # Можно добавить стиль
        )
        self.combo_quick_fmt.pack(side=LEFT, padx=5)
        # Привязываем действие: при выборе из списка запускаем функцию _on_quick_format_change
        self.combo_quick_fmt.bind("<<ComboboxSelected>>", self._on_quick_format_change)

        # Настройки
        btn_settings = ttk.Button(
            controls_frame,
            text="Настройки",
            bootstyle="outline",
            command=self._open_settings
        )
        btn_settings.pack(side=LEFT, padx=5)

        # ПРАВЫЕ КНОПКИ
        # Создаем все три кнопки сразу, но покажем только нужные

        # Кнопка СТОП (Красная)
        self.btn_stop = ttk.Button(controls_frame, text="Стоп", bootstyle="danger", command=self._stop_process)
        # Кнопка ПАУЗА (Желтая/Warning)
        self.btn_pause = ttk.Button(controls_frame, text="Пауза", bootstyle="warning", command=self._pause_process)
        # Кнопка ПРОДОЛЖИТЬ (Зеленая/Success)
        self.btn_resume = ttk.Button(controls_frame, text="Продолжить", bootstyle="success",
                                     command=self._resume_process)
        # Кнопка ЗАПУСК (Синяя/Primary)
        self.btn_start = ttk.Button(controls_frame, text="Запуск", bootstyle="primary", command=self._start_process)

        # По умолчанию видна только кнопка Запуск
        self.btn_start.pack(side=RIGHT)
        # ================================

        # 2. Таблица
        columns = ("id", "file", "format", "progress", "status")
        self.tree = ttk.Treeview(main_container, columns=columns, show="headings", selectmode="browse", height=10)
        self.tree.heading("id", text="№")
        self.tree.heading("file", text="Имя файла")
        self.tree.heading("format", text="Формат")
        self.tree.heading("progress", text="Прогресс")
        self.tree.heading("status", text="Статус")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("file", width=250)
        self.tree.column("format", width=80, anchor="center")
        self.tree.column("progress", width=150)
        self.tree.column("status", width=120)
        self.tree.pack(fill=BOTH, expand=True)

        # 3. Нижние кнопки
        list_actions_frame = ttk.Frame(main_container, padding=(0, 15))
        list_actions_frame.pack(fill=X)
        center_btn_frame = ttk.Frame(list_actions_frame)
        center_btn_frame.pack(anchor="center")
        btn_remove = ttk.Button(center_btn_frame, text="Удалить выбранное", bootstyle="outline",
                                command=self._remove_selected)
        btn_remove.pack(side=LEFT, padx=10)
        btn_clear = ttk.Button(center_btn_frame, text="Очистить очередь", bootstyle="outline",
                               command=self._clear_queue)
        btn_clear.pack(side=LEFT, padx=10)

        # 4. Лог
        ttk.Separator(main_container, orient=HORIZONTAL).pack(fill=X, pady=(0, 10))
        self.log_text = tk.Text(main_container, height=4, state="disabled", bg="#f8f9fa", relief="flat",
                                font=("Consolas", 9))
        self.log_text.pack(fill=X)
        self.status_bar_label = ttk.Label(self, text="Всего файлов: 0  Завершено: 0", font=("Helvetica", 9), anchor="w",
                                          padding=10)
        self.status_bar_label.pack(side=BOTTOM, fill=X)

    def _log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _add_files(self):
        file_paths = filedialog.askopenfilenames()
        if not file_paths: return
        settings = Settings.load()
        for path_str in file_paths:
            path = Path(path_str)
            job = Job(source_path=path, output_dir=Path(settings.output_path), profile=settings.default_profile)
            self.service.add_job(job)
            self._log(f"[INFO] Добавлен файл: {path.name}")
        self._refresh_table()

    # ЛОГИКА КНОПОК
    def _start_process(self):
        if not self.service.has_pending_jobs():
            self._log("[WARN] Нет файлов для обработки")
            return

        self.service.start_processing()
        self._processing_started = True
        self._show_running_state()
        self._log("[INFO] Обработка запущена")

    def _stop_process(self):
        self.service.stop_processing()
        self._show_idle_state()
        self._processing_started = False
        self._log("[INFO] Остановка пользователем...")

    def _pause_process(self):
        self.service.pause_processing()
        # Скрываем Паузу, показываем Продолжить
        self.btn_pause.pack_forget()
        self.btn_resume.pack(side=RIGHT, padx=5)
        # Кнопка Стоп остается на месте (мы ее перепакуем, чтобы порядок был красивый)
        self.btn_stop.pack_forget()
        self.btn_stop.pack(side=RIGHT)

        self._log("[INFO] Пауза")

    def _resume_process(self):
        self.service.resume_processing()
        # Скрываем Продолжить, показываем Паузу
        self.btn_resume.pack_forget()
        self.btn_pause.pack(side=RIGHT, padx=5)
        self.btn_stop.pack_forget()
        self.btn_stop.pack(side=RIGHT)

        self._log("[INFO] Продолжение работы")

    def _show_running_state(self):
        """Показывает кнопки [Пауза] [Стоп], скрывает [Запуск]"""
        self.btn_start.pack_forget()
        self.btn_stop.pack(side=RIGHT)
        self.btn_pause.pack(side=RIGHT, padx=5)

    def _show_idle_state(self):
        """Показывает кнопку [Запуск], скрывает остальные"""
        self.btn_stop.pack_forget()
        self.btn_pause.pack_forget()
        self.btn_resume.pack_forget()
        self.btn_start.pack(side=RIGHT)

    def _remove_selected(self):
        selected_item = self.tree.selection()
        if selected_item:
            job_id_str = selected_item[0]
            from uuid import UUID
            try:
                self.service.remove_job(UUID(job_id_str))
                self.tree.delete(job_id_str)
            except:
                pass

    def _clear_queue(self):
        self.service.clear_queue()
        self._refresh_table()
        self._log("[INFO] Очередь очищена")

    def _refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, job in enumerate(self.service.queue, 1):
            self.tree.insert("", tk.END, iid=str(job.id),
                             values=(idx, job.source_path.name, job.profile.format, f"{job.progress}%",
                                     job.state.value))
        self._update_stats()

    def _update_stats(self):
        total = len(self.service.queue)
        done = len([j for j in self.service.queue if j.state == JobState.DONE])
        self.status_bar_label.config(text=f"Всего файлов: {total}   Завершено: {done}")

    def _update_loop(self):
        try:
            # === СИНХРОНИЗАЦИЯ СОСТОЯНИЯ (НОВОЕ) ===
            # Если сервис работает, а интерфейс думает, что мы стоим (флаг False)
            if self.service._running and not self._processing_started:
                self._processing_started = True
                self._show_running_state()  # Меняем кнопки на Стоп/Пауза
                self._log("[INFO] Автоматический запуск (Горячая папка)")
            # 1. Проходимся по задачам и обновляем строки
            for job in self.service.queue:
                item_id = str(job.id)
                if self.tree.exists(item_id):
                    current_values = self.tree.item(item_id)["values"]

                    # Логика отображения статуса "Пауза"
                    state_text = job.state.value

                    # Проверяем атрибут безопасно (на случай если service.py не обновился)
                    is_paused = False
                    if hasattr(self.service, '_pause_event'):
                        is_paused = self.service._pause_event.is_set()

                    if is_paused and job.state == JobState.RUNNING:
                        state_text = "Пауза"

                    # Обновляем только если данные изменились
                    if current_values[3] != f"{job.progress}%" or current_values[4] != state_text:
                        new_values = list(current_values)
                        new_values[3] = f"{job.progress}%"
                        new_values[4] = state_text
                        self.tree.item(item_id, values=new_values)
                else:
                    self._refresh_table()
                    break

            # 2. Автоматический финиш
            if not self.service._running and self._processing_started:
                self._processing_started = False
                self._show_idle_state()
                self._log("[INFO] Все задачи выполнены")

                # Показываем финальное окно
                CustomPopup(self, "Готово", "Конвертация всех файлов завершена!", is_error=False)

                # Принудительно обновляем таблицу еще раз, чтобы показать 100%
                self._refresh_table()

        except Exception as e:
            print(f"[GUI ERROR] Ошибка в цикле обновления: {e}")
            # Если произошла ошибка, не останавливаем таймер, а пробуем снова

        self._update_stats()
        self.after(500, self._update_loop)

    def _open_settings(self):
        # Открываем модальное окно, передавая self как родителя
        SettingsWindow(self)

    def _on_quick_format_change(self, event):
        """Быстрое изменение формата через главное окно"""
        try:
            # 1. Загружаем текущие настройки
            settings = Settings.load()

            # 2. Меняем только формат в профиле
            new_fmt = self.var_quick_format.get().lower()
            settings.default_profile.format = new_fmt

            # 3. Сохраняем обратно в файл
            settings.save()

            self._log(f"[INFO] Формат вывода изменен на: {new_fmt.upper()}")

        except Exception as e:
            self._log(f"[ERROR] Не удалось сохранить формат: {e}")

    def reload_settings(self):
        """Обновляет интерфейс после изменения настроек"""
        settings = Settings.load()
        # Обновляем значение в выпадающем списке формата
        self.var_quick_format.set(settings.default_profile.format.upper())
        self._log("[INFO] Настройки обновлены")

def run_gui():
    service = ConverterService()
    app = MainWindow(service)
    app.mainloop()