# =======================================================================================
# Dosya Adı: dashboard.py
# Konum: pc/ui/dashboard.py veya pc/ui/dashboard.py
# Açıklama: Ultra modern ve profesyonel düşme algılama sistemi arayüzü (UI) bileşeni.
#
# Özellikler:
# - Premium modern tasarım: Gradient arka planlar, nöromorfik kartlar, dinamik renk şemaları
# - Modern animasyonlar: Geçiş, nabız, canlılık efektleri
# - Gelişmiş kamera görüntüleme: Canlı önizleme, FPS, yapay zeka odaklı görseller
# - Ayrıntılı olay izleme: Detay, risk, trend ve görsel raporlama
# - Bildirim merkezi: Anlık güncellemeler ve kayıtlar
# - Tema desteği: Koyu/açık mod ve özelleştirilebilir renkler
#
# Bağlantılı Dosyalar:
# - app.py, login.py, settings.py, history.py (UI yönlendirme)
# - config/settings.py, utils/logger.py (tema ve loglama)
# =======================================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import cv2
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageDraw
import numpy as np
import threading
import time
import datetime
import os
import math

class DashboardFrame(tk.Frame):
    """
    Ultra modern ve profesyonel düşme algılama sistemi arayüzü (main dashboard frame).
    """

    def __init__(self, parent, user, camera, start_fn, stop_fn, settings_fn, history_fn, logout_fn):
        """
        DashboardFrame başlatıcı (constructor) fonksiyonu.

        Args:
            parent (tk.Frame): Ana container
            user (dict): Kullanıcı bilgileri
            camera (Camera): Kamera nesnesi
            start_fn (callable): Algılama başlat fonksiyonu
            stop_fn (callable): Algılama durdur fonksiyonu
            settings_fn (callable): Ayarlar ekranı fonksiyonu
            history_fn (callable): Olay geçmişi ekranı fonksiyonu
            logout_fn (callable): Çıkış fonksiyonu
        """
        super().__init__(parent)
        self.user = user
        self.camera = camera
        self.start_fn = start_fn
        self.stop_fn = stop_fn
        self.settings_fn = settings_fn
        self.history_fn = history_fn
        self.logout_fn = logout_fn

        # Durumlar
        self.system_running = False
        self.last_frame = None
        self.last_detection = None
        self.last_detection_time = None
        self.last_detection_confidence = None
        self.update_id = None
        self.animation_id = None
        self.pulse_value = 0

        # Renk teması
        self.colors = {
            'primary': "#3F51B5",  # Ana renk - indigo
            'secondary': "#FF4081",  # Pembe
            'success': "#00C853",  # Yeşil
            'warning': "#FFC107",  # Amber
            'danger': "#F44336",  # Kırmızı
            'info': "#2196F3",    # Mavi
            'dark': "#121212",
            'light': "#F5F5F5",
            'card': "#FFFFFF",
            'text': "#333333",
            'text_secondary': "#757575",
            'border': "#E0E0E0",
            'highlight': "#E8EAF6",
            'gradient_start': "#7986CB",
            'gradient_end': "#3F51B5"
        }

        # Koyu mod için alternatif renkler
        self.dark_colors = {
            'primary': "#5C6BC0",
            'secondary': "#FF80AB",
            'success': "#69F0AE",
            'warning': "#FFD54F",
            'danger': "#FF8A80",
            'info': "#80D8FF",
            'dark': "#121212",
            'light': "#222222",
            'card': "#2C2C2C",
            'text': "#FFFFFF",
            'text_secondary': "#B0BEC5",
            'border': "#424242",
            'highlight': "#3D5AFE",
            'gradient_start': "#5C6BC0",
            'gradient_end': "#3949AB"
        }

        # Thread lock (kamera güvenliği için)
        self.frame_lock = threading.Lock()

        # İkonları yükle
        self.load_icons()
        # UI oluştur
        self._create_ui()
        # Kamera güncellemeleri başlat
        self._start_camera_updates()
        # Animasyonları başlat
        self._start_animations()

    def load_icons(self):
        """Gerekli ikonları yükler veya eksikse yer tutucu ekler."""
        self.icons = {}
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")
        icons_to_load = [
            "settings", "history", "logout", "start", "stop", "user", "camera", "alert", "logo",
            "dashboard", "notification", "eye", "refresh", "search", "export", "zoom", "info"
        ]
        for name in icons_to_load:
            path = os.path.join(icon_dir, f"{name}.png")
            try:
                if os.path.exists(path):
                    img = Image.open(path).resize((24, 24), Image.LANCZOS)
                    self.icons[name] = ImageTk.PhotoImage(img)
                else:
                    self._create_placeholder_icon(name)
            except Exception as e:
                logging.warning(f"İkon yüklenirken hata: {str(e)}")
                self._create_placeholder_icon(name)

    def _create_placeholder_icon(self, name):
        """Eksik ikonlar için basit bir yer tutucu ikonu çizer."""
        img = Image.new('RGBA', (24, 24), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        color = self.colors['primary']
        if name == "settings":
            draw.rectangle([4, 4, 20, 20], outline=color, width=2)
            draw.line([12, 4, 12, 20], fill=color, width=2)
            draw.line([4, 12, 20, 12], fill=color, width=2)
        elif name == "history":
            draw.arc([2, 2, 22, 22], 0, 270, fill=color, width=2)
            draw.line([12, 12, 18, 6], fill=color, width=2)
        elif name == "logout":
            draw.rectangle([4, 4, 20, 20], outline=self.colors['danger'], width=2)
            draw.line([14, 12, 22, 12], fill=self.colors['danger'], width=2)
            draw.line([18, 8, 22, 12], fill=self.colors['danger'], width=2)
            draw.line([18, 16, 22, 12], fill=self.colors['danger'], width=2)
        elif name == "start":
            draw.polygon([(8, 4), (20, 12), (8, 20)], fill=self.colors['success'])
        elif name == "stop":
            draw.rectangle([6, 6, 18, 18], fill=self.colors['danger'])
        else:
            draw.ellipse([2, 2, 22, 22], outline=color, width=2)
        self.icons[name] = ImageTk.PhotoImage(img)

    def _create_ui(self):
        """Tüm ana UI bileşenlerini oluşturur."""
        self.configure(bg=self.colors['light'])
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self._create_header()
        self._create_left_panel()
        self._create_right_panel()

    def _create_header(self):
        """Modern gradient başlık çubuğu ve kullanıcı bilgileri oluşturur."""
        header = tk.Canvas(self, height=70, highlightthickness=0)
        header.grid(row=0, column=0, columnspan=2, sticky="new")
        self._draw_gradient(header, self.colors['gradient_start'], self.colors['gradient_end'], width=2000, height=70)

        # Logo
        logo_frame = tk.Frame(header, bg=self.colors['primary'])
        logo_frame.place(relx=0, rely=0.5, x=25, anchor="w")
        if "logo" in self.icons:
            tk.Label(logo_frame, image=self.icons["logo"], bg=self.colors['primary']).pack(side=tk.LEFT, padx=12)
        tk.Label(
            logo_frame, text="Guard",
            font=("Segoe UI", 22, "bold"), fg="#ffffff", bg=self.colors['primary']
        ).pack(side=tk.LEFT)

        # Kullanıcı ve çıkış
        user_frame = tk.Frame(header, bg=self.colors['primary'])
        user_frame.place(relx=1, rely=0.5, x=-25, anchor="e")
        if "user" in self.icons:
            tk.Label(user_frame, image=self.icons["user"], bg=self.colors['primary']).pack(side=tk.LEFT, padx=10)
        tk.Label(
            user_frame, text=self.user.get('displayName', 'Kullanıcı'),
            font=("Segoe UI", 14, "bold"), fg="#ffffff", bg=self.colors['primary']
        ).pack(side=tk.LEFT, padx=20)
        logout_btn = tk.Button(
            user_frame, text="Çıkış Yap", font=("Segoe UI", 12, "bold"),
            bg=self.colors['danger'], fg="#ffffff", relief=tk.FLAT,
            padx=15, pady=8, command=self.logout_fn,
            activebackground="#d32f2f", activeforeground="#ffffff", cursor="hand2"
        )
        if "logout" in self.icons:
            logout_btn.config(image=self.icons["logout"], compound=tk.LEFT, padx=10)
        logout_btn.pack(side=tk.LEFT)
        logout_btn.bind("<Enter>", lambda e: logout_btn.config(bg="#d32f2f"))
        logout_btn.bind("<Leave>", lambda e: logout_btn.config(bg=self.colors['danger']))

    def _create_left_panel(self):
        """Sistem kontrolü, menü, son olay ve kart UI paneli."""
        left_panel = tk.Frame(self, bg=self.colors['light'])
        left_panel.grid(row=1, column=0, sticky="nsew", padx=25, pady=25)
        left_panel.columnconfigure(0, weight=1)

        # Sistem kontrol kartı
        control_card = self._create_neuromorphic_card(left_panel, "Sistem Kontrolü")
        control_card.pack(fill=tk.BOTH, pady=(0, 25))

        # Durum göstergesi
        status_frame = tk.Frame(control_card, bg=self.colors['card'])
        status_frame.pack(fill=tk.X, pady=12)
        self.status_var = tk.StringVar(value="Sistem Durduruldu")
        status_container = tk.Frame(status_frame, bg=self.colors['card'])
        status_container.pack(side=tk.LEFT, fill=tk.Y, padx=12)
        self.status_canvas = tk.Canvas(status_container, width=12, height=12, bg=self.colors['card'], highlightthickness=0)
        self.status_canvas.pack(side=tk.LEFT)
        self.status_indicator = self.status_canvas.create_oval(1, 1, 11, 11, fill=self.colors['danger'], outline="")
        tk.Label(
            status_container, textvariable=self.status_var,
            font=("Segoe UI", 16, "bold"), fg=self.colors['danger'], bg=self.colors['card'], padx=8
        ).pack(side=tk.LEFT)

        # Başlat/Durdur butonu
        button_frame = tk.Frame(control_card, bg=self.colors['card'], padx=12, pady=12)
        button_frame.pack(fill=tk.X)
        self.control_var = tk.StringVar(value="Sistemi Başlat")
        self.control_button = tk.Button(
            button_frame, textvariable=self.control_var, font=("Segoe UI", 14, "bold"),
            bg=self.colors['success'], fg="#ffffff", relief=tk.FLAT,
            padx=20, pady=12, command=self._toggle_system,
            activebackground="#00a742", activeforeground="#ffffff", cursor="hand2"
        )
        if "start" in self.icons:
            self.control_button.config(image=self.icons["start"], compound=tk.LEFT, padx=12)
        self.control_button.pack(fill=tk.X)
        self.control_button.bind("<Enter>", lambda e: self._button_hover_effect(self.control_button, True))
        self.control_button.bind("<Leave>", lambda e: self._button_hover_effect(self.control_button, False))

        # Sistem bilgisi
        info_frame = tk.Frame(control_card, bg="#E3F2FD", padx=12, pady=12)
        info_frame.pack(fill=tk.X, pady=12)
        info_header = tk.Frame(info_frame, bg="#E3F2FD")
        info_header.pack(fill=tk.X, pady=(0, 6))
        if "info" in self.icons:
            tk.Label(info_header, image=self.icons["info"], bg="#E3F2FD").pack(side=tk.LEFT, padx=6)
        tk.Label(
            info_header, text="Sistem Bilgisi",
            font=("Segoe UI", 12, "bold"), fg="#0D47A1", bg="#E3F2FD"
        ).pack(side=tk.LEFT)
        tk.Label(
            info_frame,
            text="Guard, yapay zeka ile düşme olaylarını algılar ve anında bildirim gönderir.",
            font=("Segoe UI", 10), fg="#0D47A1", bg="#E3F2FD",
            wraplength=260, justify=tk.LEFT
        ).pack(anchor=tk.W, pady=5)

        # Menü kartı
        menu_card = self._create_neuromorphic_card(left_panel, "Menü")
        menu_card.pack(fill=tk.BOTH, pady=(0, 25))
        for text, cmd, icon_name, color in [
            ("Ayarlar", self.settings_fn, "settings", self.colors['info']),
            ("Olay Geçmişi", self.history_fn, "history", self.colors['info'])
        ]:
            btn_container = tk.Frame(menu_card, bg=self.colors['card'], pady=6)
            btn_container.pack(fill=tk.X)
            btn = tk.Button(
                btn_container, text=text, font=("Segoe UI", 12, "bold"),
                bg=self.colors['card'], fg=color, relief=tk.FLAT,
                padx=20, pady=10, command=cmd,
                activebackground=self.colors['highlight'], activeforeground=color,
                cursor="hand2", anchor="w"
            )
            if icon_name in self.icons:
                btn.config(image=self.icons[icon_name], compound=tk.LEFT, padx=12)
            btn.pack(fill=tk.X)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.colors['highlight']))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.colors['card']))

        # Son olay kartı
        event_card = self._create_neuromorphic_card(left_panel, "Son Algılanan Olay")
        event_card.pack(fill=tk.BOTH)
        event_details = tk.Frame(event_card, bg=self.colors['card'])
        event_details.pack(fill=tk.X)
        time_frame = tk.Frame(event_details, bg=self.colors['card'], padx=12, pady=8)
        time_frame.pack(fill=tk.X)
        tk.Label(
            time_frame, text="Zaman:", font=("Segoe UI", 11, "bold"),
            fg=self.colors['text'], bg=self.colors['card']
        ).pack(side=tk.LEFT)
        self.event_time_var = tk.StringVar(value="Henüz olay algılanmadı")
        tk.Label(
            time_frame, textvariable=self.event_time_var, font=("Segoe UI", 11),
            fg=self.colors['text_secondary'], bg=self.colors['card'], padx=5
        ).pack(side=tk.LEFT)

        conf_frame = tk.Frame(event_details, bg=self.colors['card'], padx=12, pady=8)
        conf_frame.pack(fill=tk.X)
        tk.Label(
            conf_frame, text="Olasılık:", font=("Segoe UI", 11, "bold"),
            fg=self.colors['text'], bg=self.colors['card']
        ).pack(side=tk.LEFT)
        self.event_conf_var = tk.StringVar(value="")
        self.conf_value = tk.Label(
            conf_frame, textvariable=self.event_conf_var, font=("Segoe UI", 11, "bold"),
            fg=self.colors['danger'], bg=self.colors['card'], padx=5
        )
        self.conf_value.pack(side=tk.LEFT)

        risk_frame = tk.Frame(event_details, bg=self.colors['card'], padx=12, pady=8)
        risk_frame.pack(fill=tk.X)
        tk.Label(
            risk_frame, text="Risk Durumu:", font=("Segoe UI", 11, "bold"),
            fg=self.colors['text'], bg=self.colors['card']
        ).pack(side=tk.LEFT)
        self.risk_var = tk.StringVar(value="Bilinmiyor")
        self.risk_value = tk.Label(
            risk_frame, textvariable=self.risk_var, font=("Segoe UI", 11, "bold"),
            fg=self.colors['text_secondary'], bg=self.colors['card'], padx=5
        )
        self.risk_value.pack(side=tk.LEFT)

        self.event_image_frame = tk.Frame(event_card, bg=self.colors['card'], padx=12, pady=12)
        self.event_image_frame.pack(fill=tk.X)
        self.event_image_container = tk.Frame(
            self.event_image_frame, bg="#E0E0E0", width=250, height=180
        )
        self.event_image_container.pack(fill=tk.X)
        self.event_image_container.pack_propagate(False)
        self.no_image_label = tk.Label(
            self.event_image_container,
            text="Henüz düşme algılanmadı", font=("Segoe UI", 11),
            fg="#999999", bg="#E0E0E0"
        )
        self.no_image_label.pack(expand=True)
        self.event_image_label = tk.Label(self.event_image_container, bg="#E0E0E0")

        action_frame = tk.Frame(event_card, bg=self.colors['card'], padx=12, pady=12)
        action_frame.pack(fill=tk.X)
        self.export_btn = tk.Button(
            action_frame, text="Görüntüyü Kaydet", font=("Segoe UI", 10),
            bg=self.colors['card'], fg=self.colors['info'], relief=tk.FLAT,
            padx=8, pady=4, command=self._export_event_image,
            state="disabled", cursor="hand2"
        )
        if "export" in self.icons:
            self.export_btn.config(image=self.icons["export"], compound=tk.LEFT)
        self.export_btn.pack(side=tk.LEFT)
        self.details_btn = tk.Button(
            action_frame, text="Detaylar", font=("Segoe UI", 10),
            bg=self.colors['card'], fg=self.colors['info'], relief=tk.FLAT,
            padx=8, pady=4, command=self._show_event_details,
            state="disabled", cursor="hand2"
        )
        if "search" in self.icons:
            self.details_btn.config(image=self.icons["search"], compound=tk.LEFT)
        self.details_btn.pack(side=tk.RIGHT)

    def _create_right_panel(self):
        """Kamera görüntüsü ve durumunu modern şekilde gösteren panel."""
        right_panel = tk.Frame(self, bg=self.colors['light'])
        right_panel.grid(row=1, column=1, sticky="nsew", padx=15, pady=25)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        camera_card = self._create_neuromorphic_card(right_panel, "Canlı Kamera Görüntüsü")
        camera_card.pack(fill=tk.BOTH, expand=True)
        status_bar = tk.Frame(camera_card, bg=self.colors['card'], padx=12, pady=8)
        status_bar.pack(fill=tk.X)
        live_frame = tk.Frame(status_bar, bg=self.colors['card'])
        live_frame.pack(side=tk.LEFT)
        self.live_canvas = tk.Canvas(live_frame, width=10, height=10, bg=self.colors['card'], highlightthickness=0)
        self.live_canvas.pack(side=tk.LEFT)
        self.live_indicator = self.live_canvas.create_oval(1, 1, 9, 9, fill=self.colors['danger'], outline="")
        tk.Label(
            live_frame, text="CANLI", font=("Segoe UI", 11, "bold"),
            fg=self.colors['danger'], bg=self.colors['card']
        ).pack(side=tk.LEFT, padx=5)
        self.fps_var = tk.StringVar(value="0 FPS")
        tk.Label(
            status_bar, textvariable=self.fps_var, font=("Segoe UI", 11),
            fg=self.colors['text_secondary'], bg=self.colors['card']
        ).pack(side=tk.RIGHT)
        camera_display = tk.Frame(camera_card, bg="#000", width=820, height=600)
        camera_display.pack(padx=16, pady=16, expand=True)
        camera_display.pack_propagate(False)
        self.camera_label = tk.Label(camera_display, bg="#000")
        self.camera_label.pack(expand=True, fill=tk.BOTH)

    # ============================= Yardımcı UI Fonksiyonları =============================

    def _draw_gradient(self, canvas, start_color, end_color, width=800, height=70):
        """Yatay gradient arka plan çizer."""
        r1, g1, b1 = self._hex_to_rgb(start_color)
        r2, g2, b2 = self._hex_to_rgb(end_color)
        for i in range(width):
            ratio = i / width
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            canvas.create_line(i, 0, i, height, fill=color)
        canvas.config(width=width, height=height)

    def _hex_to_rgb(self, hex_color):
        """#RRGGBB renk kodunu (R, G, B) tuple'a çevirir."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _create_neuromorphic_card(self, parent, title):
        """Modern nöromorfik kart oluşturur."""
        card = tk.Frame(parent, bg=self.colors['card'], padx=16, pady=16)
        card.configure(highlightbackground=self.colors['border'], highlightthickness=2)
        tk.Label(
            card, text=title, font=("Segoe UI", 16, "bold"),
            fg=self.colors['primary'], bg=self.colors['card']
        ).pack(anchor=tk.W, pady=(0, 14))
        return card

    def _button_hover_effect(self, btn, is_hovered):
        """Modern buton hover efekti."""
        if is_hovered:
            btn.config(bg=self.colors['highlight'])
        else:
            btn.config(bg=self.colors['success'] if self.control_var.get() == "Sistemi Başlat" else self.colors['danger'])

    # ============================= Kamera ve Animasyon =============================

    def _start_camera_updates(self):
        """Kamera ve FPS güncelleyici başlatılır."""
        if self.update_id is not None:
            self.after_cancel(self.update_id)
        self._update_camera_frame()

    def _update_camera_frame(self):
        """Kamera karesi ve FPS’i modern şekilde günceller."""
        try:
            if self.camera and self.system_running:
                frame = self.camera.get_frame()
                if frame is not None and frame.size > 0:
                    with self.frame_lock:
                        self.last_frame = frame.copy()
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(frame_rgb)
                    pil_img = ImageEnhance.Brightness(pil_img).enhance(1.09)
                    pil_img = pil_img.filter(ImageFilter.SMOOTH_MORE)
                    pil_img = pil_img.resize((820, 600), Image.LANCZOS)
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self.camera_label.configure(image=tk_img)
                    self.camera_label.image = tk_img
                    if hasattr(self.camera, "fps"):
                        self.fps_var.set(f"{int(self.camera.fps)} FPS")
        except Exception as e:
            logging.error(f"Modern kamera güncellemesinde hata: {str(e)}")
        self.update_id = self.after(40, self._update_camera_frame)  # 25 FPS

    def _start_animations(self):
        """Animasyonları başlatır."""
        self._animate_live_indicator()
        self._pulse_status_indicator()

    def _animate_live_indicator(self):
        """CANLI indikatör için nabız animasyonu."""
        try:
            if self.system_running:
                color = self.colors['danger'] if time.time() % 1.2 < 0.6 else self.colors['primary']
                self.live_canvas.itemconfig(self.live_indicator, fill=color)
            else:
                self.live_canvas.itemconfig(self.live_indicator, fill=self.colors['border'])
        except:
            pass
        self.after(350, self._animate_live_indicator)

    def _pulse_status_indicator(self):
        """Nöromorfik durum göstergesi nabız animasyonu."""
        if self.system_running:
            self.pulse_value = (self.pulse_value + 1) % 20
            color_val = int(255 - 30 * abs(math.sin(self.pulse_value / 6.28)))
            self.status_canvas.itemconfig(self.status_indicator, fill=f'#{color_val:02x}c8{83:02x}')
        else:
            self.status_canvas.itemconfig(self.status_indicator, fill=self.colors['danger'])
        self.after(120, self._pulse_status_indicator)

    # ============================= Olay ve Popup Yönetimi =============================

    def update_system_status(self, running):
        """Sistem başlat/durdur durumunu UI’da günceller."""
        self.system_running = running
        if running:
            self.status_var.set("Sistem Aktif")
            self.status_canvas.itemconfig(self.status_indicator, fill=self.colors['success'])
            self.control_var.set("Sistemi Durdur")
            self.control_button.config(bg=self.colors['danger'], image=self.icons.get("stop"))
        else:
            self.status_var.set("Sistem Durduruldu")
            self.status_canvas.itemconfig(self.status_indicator, fill=self.colors['danger'])
            self.control_var.set("Sistemi Başlat")
            self.control_button.config(bg=self.colors['success'], image=self.icons.get("start"))

    def update_fall_detection(self, screenshot, confidence, event_data):
        """Düşme olayını ultra modern şekilde gösterir."""
        try:
            with self.frame_lock:
                self.last_detection = screenshot.copy()
                self.last_detection_time = event_data.get("timestamp", time.time())
                self.last_detection_confidence = confidence

            dt = datetime.datetime.fromtimestamp(self.last_detection_time)
            self.event_time_var.set(dt.strftime("%d.%m.%Y %H:%M:%S"))
            self.event_conf_var.set(f"%{confidence * 100:.2f}")

            if confidence > 0.8:
                risk = "Yüksek"
                color = self.colors['danger']
            elif confidence > 0.6:
                risk = "Orta"
                color = self.colors['warning']
            else:
                risk = "Düşük"
                color = self.colors['success']
            self.risk_var.set(risk)
            self.conf_value.config(fg=color)
            self.risk_value.config(fg=color)

            self.no_image_label.pack_forget()
            detection_rgb = cv2.cvtColor(self.last_detection, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(detection_rgb).resize((250, 180), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(pil_img)
            self.event_image_label.configure(image=tk_img)
            self.event_image_label.image = tk_img
            self.event_image_label.pack(fill=tk.BOTH, expand=True)
            self.export_btn.config(state="normal")
            self.details_btn.config(state="normal")
            self._show_fall_alert(confidence)
        except Exception as e:
            logging.error(f"Ultra modern düşme olayı güncellenirken hata: {str(e)}")

    def _show_fall_alert(self, confidence):
        """Düşme algılandığında modern pop-up gösterir."""
        alert = tk.Toplevel(self)
        alert.title("Düşme Algılandı!")
        alert.geometry("470x370+500+200")
        alert.configure(bg=self.colors['card'])
        alert.transient(self)
        alert.grab_set()
        header = tk.Canvas(alert, height=90, highlightthickness=0)
        self._draw_gradient(header, self.colors['danger'], self.colors['primary'], width=470, height=90)
        header.pack(fill=tk.X)
        if "alert" in self.icons:
            tk.Label(header, image=self.icons["alert"], bg=self.colors['danger']).place(x=14, y=14)
        tk.Label(
            header, text="DÜŞME ALGILANDI!", font=("Segoe UI", 18, "bold"),
            fg="#fff", bg=self.colors['danger']
        ).place(relx=0.5, rely=0.5, anchor="center")
        content = tk.Frame(alert, bg=self.colors['card'], padx=25, pady=25)
        content.pack(fill=tk.BOTH, expand=True)
        tk.Label(content, text="Yapay zeka bir düşme olayı tespit etti!",
                 font=("Segoe UI", 14, "bold"), fg=self.colors['text'], bg=self.colors['card']).pack(pady=10)
        tk.Label(content, text=f"Düşme Olasılığı: %{confidence * 100:.2f}",
                 font=("Segoe UI", 12), fg=self.colors['danger'], bg=self.colors['card']).pack()
        risk = "Yüksek" if confidence > 0.8 else "Orta" if confidence > 0.6 else "Düşük"
        risk_color = self.colors['danger'] if confidence > 0.8 else self.colors['warning'] if confidence > 0.6 else self.colors['success']
        tk.Label(content, text=f"Risk Seviyesi: {risk}",
                 font=("Segoe UI", 12), fg=risk_color, bg=self.colors['card']).pack(pady=7)
        tk.Label(content, text="Bildirimler ilgili kişilere gönderildi.",
                 font=("Segoe UI", 11), fg=self.colors['text_secondary'], bg=self.colors['card']).pack(pady=7)
        tk.Button(content, text="Tamam", font=("Segoe UI", 12, "bold"),
                  bg=self.colors['info'], fg="#fff", relief=tk.FLAT, padx=25, pady=10,
                  command=alert.destroy, activebackground="#1976d2",
                  activeforeground="#fff", cursor="hand2").pack(pady=12)
        try:
            import winsound
            winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
        except:
            logging.warning("Modern sesli uyarı çalınamadı.")

    def _export_event_image(self):
        """Olay görüntüsünü masaüstüne kaydeder."""
        if self.last_detection is not None:
            now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fall_event_{now}.jpg"
            path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
            cv2.imwrite(path, self.last_detection)
            messagebox.showinfo("Kayıt Başarılı", f"Görüntü başarıyla kaydedildi:\n{path}")

    def _show_event_details(self):
        """Detayları popup ile gösterir (gelişmiş analiz eklenebilir)."""
        messagebox.showinfo("Olay Detayı", "Olay geçmişi ve analizleri burada görünecek (beta).")

    def on_destroy(self):
        """Frame yok edilirken timer ve animasyonları durdurur."""
        try:
            if self.update_id is not None:
                self.after_cancel(self.update_id)
                self.update_id = None
            if self.animation_id is not None:
                self.after_cancel(self.animation_id)
                self.animation_id = None
        except Exception as e:
            logging.error(f"Dashboard destroy sırasında hata: {str(e)}")

    def _toggle_system(self):
        """Sistemi başlat/durdur butonu için çağrılır."""
        try:
            if not self.system_running:
                self.start_fn()
            else:
                self.stop_fn()
        except Exception as e:
            logging.error(f"Sistem başlatılırken/durdurulurken hata: {str(e)}")
            messagebox.showerror("Hata", "Sistem başlatılamadı veya durdurulamadı.")
