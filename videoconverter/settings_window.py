import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog

from .models import Settings, FormatProfile

class CustomPopup(tk.Toplevel):
    def __init__(self, parent, title, message, is_error=False):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Рамка
        wrapper = tk.Frame(self, highlightbackground="black", highlightthickness=1, borderwidth=0)
        wrapper.pack(fill=tk.BOTH, expand=True)

        # Контент
        container = ttk.Frame(wrapper, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Иконка (символ) и текст
        icon_char = "!" if is_error else "i"
        icon_style = "danger" if is_error else "primary"

        # Красивый кружок с буквой
        lbl_icon = ttk.Label(
            container,
            text=icon_char,
            font=("Helvetica", 16, "bold"),
            bootstyle=f"inverse-{icon_style}",
            width=3,
            anchor="center"
        )
        lbl_icon.pack(side=tk.LEFT, padx=(0, 15), anchor="n")

        lbl_msg = ttk.Label(container, text=message, font=("Helvetica", 10), wraplength=280)
        lbl_msg.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Кнопка ОК
        btn_frame = ttk.Frame(wrapper, padding=15)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_frame, text="OK", command=self.destroy, bootstyle="primary", width=10).pack(side=tk.RIGHT)

        # Центрируем относительно родителя
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()  # Показываем


class SettingsWindow(ttk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Настройки")
        self.geometry("600x580")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self.current_settings = Settings.load()

        self._init_ui()
        self._load_values()

    def _validate_digits(self, new_value):
        if new_value == "": return True
        return new_value.isdigit()

    def _init_ui(self):
        vcmd = (self.register(self._validate_digits), '%P')

        # ОБЕРТКА ДЛЯ РАМКИ
        wrapper = tk.Frame(self, highlightbackground="black", highlightthickness=1, borderwidth=0)
        wrapper.pack(fill=tk.BOTH, expand=True)

        container = ttk.Frame(wrapper, padding=20)
        container.pack(fill=BOTH, expand=True)

        # БЛОК 1: Основные параметры
        lbl_general = ttk.Label(container, text="Основные параметры", font=("Helvetica", 12, "bold"))
        lbl_general.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(container, text="Папка для сохранения:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.var_output_path = ttk.StringVar()
        entry_out = ttk.Entry(container, textvariable=self.var_output_path)
        entry_out.grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(container, text="Обзор...", bootstyle="outline", command=self._browse_output).grid(row=1, column=2,
                                                                                                      padx=5)

        self.var_hot_enabled = ttk.BooleanVar()
        chk_hot = ttk.Checkbutton(container, text="Использовать горячую папку", variable=self.var_hot_enabled,
                                  bootstyle="round-toggle")
        chk_hot.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(container, text="Путь горячей папки:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.var_hot_path = ttk.StringVar()
        entry_hot = ttk.Entry(container, textvariable=self.var_hot_path)
        entry_hot.grid(row=3, column=1, sticky="ew", padx=5)
        ttk.Button(container, text="Обзор...", bootstyle="outline", command=self._browse_hot).grid(row=3, column=2,
                                                                                                   padx=5)

        self.var_notify = ttk.BooleanVar()
        chk_notify = ttk.Checkbutton(container, text="Показывать уведомления после завершения",
                                     variable=self.var_notify, bootstyle="round-toggle")
        chk_notify.grid(row=4, column=1, sticky="w", padx=5, pady=5)

        ttk.Separator(container, orient=HORIZONTAL).grid(row=5, column=0, columnspan=3, sticky="ew", pady=20)

        # БЛОК 2: Параметры конвертации
        lbl_conv = ttk.Label(container, text="Параметры по умолчанию для конвертации", font=("Helvetica", 12, "bold"))
        lbl_conv.grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(container, text="Формат").grid(row=7, column=0, sticky="e", padx=5, pady=5)
        self.var_format = ttk.StringVar()
        combo_fmt = ttk.Combobox(container, textvariable=self.var_format, state="readonly")
        combo_fmt['values'] = ('MP4', 'AVI', 'MKV', 'MOV', 'WMV')
        combo_fmt.grid(row=7, column=1, sticky="ew", padx=5)

        ttk.Label(container, text="Видео-кодек").grid(row=8, column=0, sticky="e", padx=5, pady=5)
        self.var_vcodec = ttk.StringVar()
        combo_vcodec = ttk.Combobox(container, textvariable=self.var_vcodec, state="readonly")
        combo_vcodec['values'] = ('h264', 'hevc', 'mpeg4', 'copy')
        combo_vcodec.grid(row=8, column=1, sticky="ew", padx=5)

        ttk.Label(container, text="Аудио-кодек").grid(row=9, column=0, sticky="e", padx=5, pady=5)
        self.var_acodec = ttk.StringVar()
        combo_acodec = ttk.Combobox(container, textvariable=self.var_acodec, state="readonly")
        combo_acodec['values'] = ('aac', 'mp3', 'ac3', 'copy')
        combo_acodec.grid(row=9, column=1, sticky="ew", padx=5)

        ttk.Label(container, text="Разрешение").grid(row=10, column=0, sticky="e", padx=5, pady=5)
        res_frame = ttk.Frame(container)
        res_frame.grid(row=10, column=1, sticky="ew", padx=5)
        self.var_width = ttk.StringVar()
        self.var_height = ttk.StringVar()
        ttk.Entry(res_frame, textvariable=self.var_width, width=6, validate="key", validatecommand=vcmd).pack(side=LEFT)
        ttk.Label(res_frame, text="x").pack(side=LEFT, padx=5)
        ttk.Entry(res_frame, textvariable=self.var_height, width=6, validate="key", validatecommand=vcmd).pack(
            side=LEFT)

        ttk.Label(container, text="Битрейт").grid(row=11, column=0, sticky="e", padx=5, pady=5)
        bitrate_frame = ttk.Frame(container)
        bitrate_frame.grid(row=11, column=1, sticky="ew", padx=5)
        self.var_bitrate = ttk.StringVar()
        combo_bitrate = ttk.Combobox(bitrate_frame, textvariable=self.var_bitrate, width=8, state="readonly")
        combo_bitrate['values'] = ('1', '2', '4', '6', '8', '10', '15', '20')
        combo_bitrate.pack(side=LEFT)
        ttk.Label(bitrate_frame, text="Мбит/с").pack(side=LEFT, padx=5)

        ttk.Label(container, text="FPS").grid(row=12, column=0, sticky="e", padx=5, pady=5)
        self.var_fps = ttk.IntVar()
        fps_combo = ttk.Combobox(container, textvariable=self.var_fps, values=[24, 25, 30, 60], state="readonly")
        fps_combo.grid(row=12, column=1, sticky="ew", padx=5)

        container.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(wrapper, padding=20)
        btn_frame.pack(fill=X, side=BOTTOM)
        ttk.Button(btn_frame, text="Отмена", bootstyle="secondary", command=self.destroy).pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="Сохранить", bootstyle="primary", command=self._save_settings).pack(side=RIGHT,
                                                                                                       padx=5)

    def _browse_output(self):
        path = filedialog.askdirectory(parent=self)
        if path: self.var_output_path.set(path)

    def _browse_hot(self):
        path = filedialog.askdirectory(parent=self)
        if path: self.var_hot_path.set(path)

    def _load_values(self):
        s = self.current_settings
        self.var_output_path.set(s.output_path)
        self.var_hot_enabled.set(s.hot_folder_enabled)
        self.var_hot_path.set(s.hot_folder_path)
        self.var_notify.set(s.notifications_enabled)
        p = s.default_profile
        self.var_format.set(p.format.upper())
        self.var_vcodec.set(p.video_codec)
        self.var_acodec.set(p.audio_codec)
        self.var_fps.set(p.fps)
        if p.bitrate and p.bitrate.endswith("M"):
            self.var_bitrate.set(p.bitrate[:-1])
        else:
            self.var_bitrate.set(p.bitrate)
        if "x" in p.resolution:
            try:
                w, h = p.resolution.split("x")
                self.var_width.set(w)
                self.var_height.set(h)
            except ValueError:
                self.var_width.set("1920")
                self.var_height.set("1080")
        else:
            self.var_width.set("1920")
            self.var_height.set("1080")

    def _save_settings(self):
        try:
            w = self.var_width.get().strip()
            h = self.var_height.get().strip()
            if not w or not h: raise ValueError("Поля разрешения не могут быть пустыми")
            full_resolution = f"{w}x{h}"

            bitrate_val = self.var_bitrate.get()
            if bitrate_val.isdigit(): bitrate_val += "M"

            new_profile = FormatProfile(
                format=self.var_format.get().lower(),
                video_codec=self.var_vcodec.get(),
                audio_codec=self.var_acodec.get(),
                resolution=full_resolution,
                bitrate=bitrate_val,
                fps=int(self.var_fps.get())
            )

            new_settings = Settings(
                output_path=self.var_output_path.get(),
                hot_folder_enabled=self.var_hot_enabled.get(),
                hot_folder_path=self.var_hot_path.get(),
                notifications_enabled=self.var_notify.get(),
                default_profile=new_profile
            )

            new_settings.save()
            if hasattr(self.master, "reload_settings"):
                self.master.reload_settings()
            CustomPopup(self, "Настройки", "Настройки успешно сохранены!", is_error=False)

        except Exception as e:
            CustomPopup(self, "Ошибка сохранения", f"Некорректные данные:\n{e}", is_error=True)