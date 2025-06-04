# =======================================================================================
# 📄 Dosya Adı: dashboard.py
# 📁 Konum: guard_pc_app/ui/dashboard.py
# 📌 Açıklama:
# Ultra modern ve profesyonel insan takibi ve düşme algılama sistemi arayüzü (UI) bileşeni.
# Tasarım modernize edildi: Şık gradientler, nöromorfik efektler, akıcı animasyonlar.
# Çoklu kamera desteği: Camera sınıfı ile entegrasyon.
# YOLOv11 pose estimation (yolo11l-pose.pt) ile insan takibi (DeepSORT) ve düşme algılama.
# Sol panele "Son Düşme Olayı" kartı eklendi (zaman, güven skoru, takip ID'si).
#
# Özellikler:
# - Premium modern tasarım: Gelişmiş gradient arka planlar, nöromorfik kartlar, dinamik renk şemaları
# - Modern animasyonlar: Geçiş, nabız, canlılık efektleri
# - Gelişmiş kamera görüntüleme: Çoklu kamera önizleme, FPS, yapay zeka odaklı görseller
# - Ayrıntılı olay izleme: Düşme olayları için zaman, güven ve takip ID'si
# - Bildirim merkezi: Anlık düşme bildirimleri
# - Tema desteği: Koyu/açık mod ve özelleştirilebilir renkler
#
# 🔗 Bağlantılı Dosyalar:
# - app.py, login.py, settings.py, history.py (UI yönlendirme)
# - config/settings.py, utils/logger.py (tema ve loglama)
# - core/camera.py (çoklu kamera yönetimi)
# - core/fall_detection.py (YOLOv11 insan takibi ve düşme algılama)
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
import winsound
from core.fall_detection import FallDetector  # İnsan takibi ve düşme algılama için import

class DashboardFrame(tk.Frame):
    """
    Ultra modern ve profesyonel insan takibi ve düşme algılama sistemi arayüzü.
    """

    def __init__(self, parent, user, cameras, start_fn, stop_fn, settings_fn, history_fn, logout_fn):
        """
        DashboardFrame başlatıcı fonksiyonu.

        Args:
            parent (tk.Frame): Ana container
            user (dict): Kullanıcı bilgileri
            cameras (list): Kamera örneklerinin listesi
            start_fn (callable): Algılama başlat fonksiyonu
            stop_fn (callable): Algılama durdur fonksiyonu
            settings_fn (callable): Ayarlar ekranı fonksiyonu
            history_fn (callable): Olay geçmişi ekranı fonksiyonu
            logout_fn (callable): Çıkış fonksiyonu
        """
        super().__init__(parent)
        self.user = user
        self.cameras = cameras
        self.start_fn = start_fn
        self.stop_fn = stop_fn
        self.settings_fn = settings_fn
        self.history_fn = history_fn
        self.logout_fn = logout_fn

        # Durumlar
        self.system_running = False
        self.last_frames = {f"camera_{cam.camera_index}": None for cam in cameras}
        self.last_detection_time = None
        self.last_detection_confidence = 0.0
        self.last_track_id = None
        self.update_id = None
        self.animation_id = None
        self.pulse_value = 0
        self.is_destroyed = False
        self.bind("<Destroy>", self._on_widget_destroy)

        # Renk teması
        self.colors = {
            'primary': "#6B46C1", 'secondary': "#FF6B81", 'success': "#38B2AC",
            'warning': "#F6AD55", 'danger': "#E53E3E", 'info': "#3182CE",
            'dark': "#1A202C", 'light': "#F7FAFC", 'card': "#FFFFFF",
            'text': "#1A202C", 'text_secondary': "#718096", 'border': "#E2E8F0",
            'highlight': "#EDF2F7", 'gradient_start': "#B794F4", 'gradient_end': "#6B46C1"
        }
        self.dark_colors = {
            'primary': "#9F7AEA", 'secondary': "#F687B3", 'success': "#4FD1C5",
            'warning': "#F6AD55", 'danger': "#F56565", 'info': "#63B3ED",
            'dark': "#171923", 'light': "#2D3748", 'card': "#1A202C",
            'text': "#E2E8F0", 'text_secondary': "#A0AEC0", 'border': "#4A5568",
            'highlight': "#5A67D8", 'gradient_start': "#D6BCFA", 'gradient_end': "#9F7AEA"
        }

        # Kamera durumları
        self.current_camera_id = f"camera_{cameras[0].camera_index}" if cameras else None
        self.frame_locks = {f"camera_{cam.camera_index}": threading.Lock() for cam in cameras}
        self.camera_labels = {}
        self.fps_vars = {f"camera_{cam.camera_index}": tk.StringVar(value="0 FPS") for cam in cameras}
        self.live_indicators = {}

        # Son düşme olayı değişkenleri
        self.event_time_var = tk.StringVar(value="Zaman: -")
        self.event_conf_var = tk.StringVar(value="Güven: -")
        self.event_id_var = tk.StringVar(value="ID: -")

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
            "dashboard", "notification", "eye", "refresh", "search", "export", "zoom", "info",
            "camera_select"
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
        elif name == "camera_select":
            draw.rectangle([4, 4, 20, 16], outline=color, width=2)
            draw.polygon([(8, 16), (12, 20), (16, 16)], fill=color)
        else:
            draw.ellipse([2, 2, 22, 22], outline=color, width=2)
        self.icons[name] = ImageTk.PhotoImage(img)

    def _create_ui(self):
        """Tüm ana UI bileşenlerini oluşturur."""
        # Ana çerçeve arka planı
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
        # Header canvas'ı gradient arka plan ile
        header = tk.Canvas(self, height=70, highlightthickness=0, bg=self.colors['light'])
        self._draw_gradient(header, self.colors['gradient_start'], self.colors['gradient_end'], width=2000, height=70)
        header.grid(row=0, column=0, columnspan=2, sticky="new")
        header.create_rectangle(0, 68, 2000, 70, fill="#000000", outline="")

        # Logo çerçevesi
        logo_frame = tk.Frame(header, bg=self.colors['light'], bd=0, highlightthickness=0)
        logo_frame.place(relx=0, rely=0.5, x=25, anchor="w")
        if "logo" in self.icons:
            tk.Label(logo_frame, image=self.icons["logo"], bg=self.colors['light']).pack(side=tk.LEFT, padx=12)
        tk.Label(
            logo_frame, text="Guard",
            font=("Roboto", 24, "bold"), fg="#ffffff", bg=self.colors['light']
        ).pack(side=tk.LEFT)

        # Kullanıcı ve çıkış çerçevesi
        user_frame = tk.Frame(header, bg=self.colors['light'])
        user_frame.place(relx=1, rely=0.5, x=-25, anchor="e")
        if "user" in self.icons:
            tk.Label(user_frame, image=self.icons["user"], bg=self.colors['light']).pack(side=tk.LEFT, padx=10)
        tk.Label(
            user_frame, text=self.user.get('displayName', 'Kullanıcı'),
            font=("Helvetica", 14, "bold"), fg="#ffffff", bg=self.colors['light']
        ).pack(side=tk.LEFT, padx=20)
        logout_btn = tk.Button(
            user_frame, text="Çıkış Yap", font=("Helvetica", 12, "bold"),
            bg=self.colors['danger'], fg="#ffffff", relief=tk.FLAT,
            padx=15, pady=8, command=self.logout_fn,
            activebackground="#C62828", activeforeground="#ffffff", cursor="hand2"
        )
        if "logout" in self.icons:
            logout_btn.config(image=self.icons["logout"], compound=tk.LEFT, padx=10)
        logout_btn.pack(side=tk.LEFT)
        logout_btn.bind("<Enter>", lambda e: logout_btn.config(bg="#C62828"))
        logout_btn.bind("<Leave>", lambda e: logout_btn.config(bg=self.colors['danger']))

    def _create_left_panel(self):
        """Sistem kontrolü, menü ve son düşme olayı paneli."""
        left_panel = tk.Frame(self, bg=self.colors['light'])
        left_panel.grid(row=1, column=0, sticky="nsew", padx=25, pady=25)
        left_panel.columnconfigure(0, weight=1)

        # Sistem kontrol kartı
        control_card = self._create_neuromorphic_card(left_panel, "Sistem Kontrolü")
        control_card.pack(fill=tk.BOTH, pady=(0, 25))

        # Kamera seçimi
        camera_select_frame = tk.Frame(control_card, bg=self.colors['card'])
        camera_select_frame.pack(fill=tk.X, pady=8)
        tk.Label(
            camera_select_frame, text="Kamera:", font=("Helvetica", 12, "bold"),
            fg=self.colors['text'], bg=self.colors['card']
        ).pack(side=tk.LEFT, padx=12)
        self.camera_var = tk.StringVar(value=self.current_camera_id or "Kamera Seç")
        camera_menu = ttk.Combobox(
            camera_select_frame, textvariable=self.camera_var,
            values=[f"camera_{cam.camera_index}" for cam in self.cameras],
            state="readonly", width=20, font=("Arial", 11)
        )
        camera_menu.pack(side=tk.LEFT, padx=12)
        camera_menu.bind("<<ComboboxSelected>>", self._on_camera_select)

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
            font=("Helvetica", 16, "bold"), fg=self.colors['danger'], bg=self.colors['card'], padx=8
        ).pack(side=tk.LEFT)

        # Başlat/Durdur butonu
        button_frame = tk.Frame(control_card, bg=self.colors['card'], padx=12, pady=12)
        button_frame.pack(fill=tk.X)
        self.control_var = tk.StringVar(value="Sistemi Başlat")
        self.control_button = tk.Button(
            button_frame, textvariable=self.control_var, font=("Helvetica", 14, "bold"),
            bg=self.colors['success'], fg="#ffffff", relief=tk.FLAT,
            padx=20, pady=12, command=self._toggle_system,
            activebackground="#2C7A7B", activeforeground="#ffffff", cursor="hand2"
        )
        if "start" in self.icons:
            self.control_button.config(image=self.icons["start"], compound=tk.LEFT, padx=12)
        self.control_button.pack(fill=tk.X)
        self.control_button.bind("<Enter>", lambda e: self._button_hover_effect(self.control_button, True))
        self.control_button.bind("<Leave>", lambda e: self._button_hover_effect(self.control_button, False))
        self._animate_button_pulse()

        # Sistem bilgisi
        info_frame = tk.Frame(control_card, bg="#EBF4FF", padx=12, pady=12)
        info_frame.pack(fill=tk.X, pady=12)
        info_header = tk.Frame(info_frame, bg="#EBF4FF")
        info_header.pack(fill=tk.X, pady=(0, 6))
        if "info" in self.icons:
            tk.Label(info_header, image=self.icons["info"], bg="#EBF4FF").pack(side=tk.LEFT, padx=6)
        tk.Label(
            info_header, text="Sistem Bilgisi",
            font=("Helvetica", 12, "bold"), fg="#2B6CB0", bg="#EBF4FF"
        ).pack(side=tk.LEFT)
        tk.Label(
            info_frame,
            text="Guard, yapay zeka ile insanları takip eder ve düşme olaylarını algılar.",
            font=("Helvetica", 10), fg="#2B6CB0", bg="#EBF4FF",
            wraplength=260, justify=tk.LEFT
        ).pack(anchor=tk.W, pady=5)

        # Son Düşme Olayı kartı
        event_card = self._create_neuromorphic_card(left_panel, "Son Düşme Olayı")
        event_card.pack(fill=tk.BOTH, pady=(0, 25))
        tk.Label(
            event_card, textvariable=self.event_time_var, font=("Arial", 12),
            fg=self.colors['text'], bg=self.colors['card']
        ).pack(anchor=tk.W, padx=12, pady=2)
        tk.Label(
            event_card, textvariable=self.event_conf_var, font=("Arial", 12),
            fg=self.colors['text'], bg=self.colors['card']
        ).pack(anchor=tk.W, padx=12, pady=2)
        tk.Label(
            event_card, textvariable=self.event_id_var, font=("Arial", 12),
            fg=self.colors['text'], bg=self.colors['card']
        ).pack(anchor=tk.W, padx=12, pady=2)

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
                btn_container, text=text, font=("Helvetica", 12, "bold"),
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

    def _create_right_panel(self):
        """Kamera görüntülerini sekmeli şekilde gösteren panel."""
        right_panel = tk.Frame(self, bg=self.colors['light'])
        right_panel.grid(row=1, column=1, sticky="nsew", padx=20, pady=25)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)

        camera_card = self._create_neuromorphic_card(right_panel, "Canlı Kamera Görüntüleri")
        camera_card.pack(fill=tk.BOTH, expand=True)

        # Sekme paneli
        notebook = ttk.Notebook(camera_card)
        notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # Her kamera için sekme oluştur
        for camera in self.cameras:
            camera_id = f"camera_{camera.camera_index}"
            tab = tk.Frame(notebook, bg=self.colors['card'])
            notebook.add(tab, text=f"Kamera {camera.camera_index}")
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=0)
            tab.rowconfigure(1, weight=1)

            # Durum çubuğu
            status_bar = tk.Frame(tab, bg=self.colors['card'], padx=12, pady=8)
            status_bar.pack(fill=tk.X)
            live_frame = tk.Frame(status_bar, bg=self.colors['card'])
            live_frame.pack(side=tk.LEFT)
            live_canvas = tk.Canvas(live_frame, width=10, height=10, bg=self.colors['card'], highlightthickness=0)
            live_canvas.pack(side=tk.LEFT)
            live_indicator = live_canvas.create_oval(1, 1, 9, 9, fill=self.colors['danger'], outline="")
            tk.Label(
                live_frame, text="CANLI", font=("Helvetica", 11, "bold"),
                fg=self.colors['danger'], bg=self.colors['card']
            ).pack(side=tk.LEFT, padx=5)
            tk.Label(
                status_bar, textvariable=self.fps_vars[camera_id], font=("Helvetica", 11),
                fg=self.colors['text_secondary'], bg=self.colors['card']
            ).pack(side=tk.RIGHT)

            # Kamera ekranı
            camera_display = tk.Frame(tab, bg="#1A202C", width=820, height=600)
            camera_display.pack(padx=16, pady=16, expand=True)
            camera_display.pack_propagate(False)
            camera_label = tk.Label(camera_display, bg="#1A202C")
            camera_label.pack(expand=True, fill=tk.BOTH)
            self.camera_labels[camera_id] = camera_label
            self.live_indicators[camera_id] = (live_canvas, live_indicator)

    # ============================= Yardımcı UI Fonksiyonları =============================

    def _draw_gradient(self, canvas, start_color, end_color, width=800, height=70):
        """Yatay gradient arka plan çizer."""
        r1, g1, b1 = self._hex_to_rgb(start_color)
        r2, g2, b2 = self._hex_to_rgb(end_color)
        steps = 150
        for i in range(steps):
            ratio = i / (steps - 1)
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            x0 = i * width / steps
            x1 = (i + 1) * width / steps
            canvas.create_rectangle(x0, 0, x1, height, fill=color, outline="")
        canvas.config(width=width, height=height)

    def _hex_to_rgb(self, hex_color):
        """#RRGGBB renk kodunu (R, G, B) tuple'a çevirir."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _create_neuromorphic_card(self, parent, title):
        """Modern nöromorfik kart oluşturur."""
        card = tk.Frame(parent, bg=self.colors['card'], padx=16, pady=16)
        card.configure(
            highlightbackground=self.colors['border'], highlightthickness=1,
            borderwidth=0, relief="flat"
        )
        shadow_canvas = tk.Canvas(card, bg=self.colors['light'], highlightthickness=0, height=12)
        shadow_canvas.pack(fill=tk.X, side=tk.BOTTOM)
        shadow_canvas.create_rectangle(0, 0, 2000, 12, fill="#E0E0E0", outline="")
        tk.Label(
            card, text=title, font=("Helvetica", 16, "bold"),
            fg=self.colors['primary'], bg=self.colors['card']
        ).pack(anchor=tk.W, pady=(0, 14))
        return card

    def _button_hover_effect(self, btn, is_hovered):
        """Modern buton hover efekti."""
        if is_hovered:
            btn.config(bg=self.colors['highlight'])
        else:
            btn.config(bg=self.colors['success'] if self.control_var.get() == "Sistemi Başlat" else self.colors['danger'])

    def _animate_button_pulse(self):
        """Başlat/Durdur butonuna nabız efekti ekler."""
        def safe_pulse():
            if self.is_destroyed or not self.winfo_exists():
                return
            if self.system_running:
                alpha = 0.85 + 0.15 * math.sin(self.pulse_value / 8)
                color = self.colors['danger']
                r, g, b = self._hex_to_rgb(color)
                pulse_color = f'#{int(r*alpha):02x}{int(g*alpha):02x}{int(b*alpha):02x}'
                self.control_button.config(bg=pulse_color)
                self.pulse_value = (self.pulse_value + 1) % 20
            else:
                self.control_button.config(bg=self.colors['success'])
            self.after(80, safe_pulse)

        self._safe_widget_operation(safe_pulse)

    def _on_widget_destroy(self, event):
        """Widget yok edildiğinde çağrılır."""
        if event.widget == self:
            logging.info("Dashboard widget yok ediliyor...")
            self.is_destroyed = True
            self._cleanup_resources()

    def _cleanup_resources(self):
        """Kaynakları temizler."""
        try:
            if hasattr(self, 'update_id') and self.update_id:
                self.after_cancel(self.update_id)
                self.update_id = None
            if hasattr(self, 'animation_id') and self.animation_id:
                self.after_cancel(self.animation_id)
                self.animation_id = None
            if hasattr(self, 'anim_ids'):
                for anim_id in self.anim_ids:
                    try:
                        self.after_cancel(anim_id)
                    except:
                        pass
                self.anim_ids.clear()
            logging.info("Dashboard kaynakları temizlendi")
        except Exception as e:
            logging.error(f"Dashboard kaynak temizleme hatası: {e}")

    def _safe_widget_operation(self, operation, *args, **kwargs):
        """Widget operasyonlarını güvenli şekilde yapar."""
        try:
            if self.is_destroyed or not self.winfo_exists():
                return False
            return operation(*args, **kwargs)
        except tk.TclError as e:
            if "invalid command name" in str(e):
                logging.warning("Widget artık mevcut değil, operasyon iptal edildi")
                self.is_destroyed = True
                return False
            raise

    # ============================= Kamera ve Animasyon =============================

    def _start_camera_updates(self):
        """Güvenli kamera güncelleyici başlatır."""
        if self.update_id is not None:
            self.after_cancel(self.update_id)
        self._update_camera_frame()

    def _update_camera_frame(self):
        """Güvenli kamera karesi güncelleme (Camera sınıfı ile entegrasyon)."""
        def safe_update():
            try:
                if self.is_destroyed or not self.winfo_exists():
                    return

                fall_detector = FallDetector.get_instance()
                for camera in self.cameras:
                    camera_id = f"camera_{camera.camera_index}"
                    if self.system_running:
                        frame = camera.get_frame()
                        if frame is not None and frame.size > 0:
                            with self.frame_locks[camera_id]:
                                self.last_frames[camera_id] = frame.copy()

                            # İnsan takibi ve kare çizimi
                            annotated_frame, tracks = fall_detector.get_detection_visualization(frame)

                            # Düşme algılama
                            is_fall, confidence, track_id = fall_detector.detect_fall(frame, tracks)
                            if is_fall and confidence > 0.5:
                                now = datetime.datetime.now()
                                self.last_detection_time = now
                                self.last_detection_confidence = confidence
                                self.last_track_id = track_id
                                self.event_time_var.set(f"Zaman: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                                self.event_conf_var.set(f"Güven: {confidence:.2f}")
                                self.event_id_var.set(f"ID: {track_id}")
                                logging.info(f"Düşme algılandı: ID={track_id}, Güven={confidence}, Zaman={now}")
                                self._show_fall_alert()

                            # Görüntüyü güncelle
                            frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                            pil_img = Image.fromarray(frame_rgb)
                            pil_img = ImageEnhance.Brightness(pil_img).enhance(1.09)
                            pil_img = pil_img.resize((820, 600), Image.LANCZOS)
                            tk_img = ImageTk.PhotoImage(pil_img)

                            if not self.is_destroyed and self.winfo_exists():
                                self.camera_labels[camera_id].configure(image=tk_img)
                                self.camera_labels[camera_id].image = tk_img
                                self.fps_vars[camera_id].set(f"{int(camera.fps)} FPS")
            except tk.TclError as e:
                if "invalid command name" in str(e):
                    self.is_destroyed = True
                    return
                logging.error(f"Kamera güncelleme hatası: {e}")
            except Exception as e:
                logging.error(f"Kamera güncelleme hatası: {e}")

        self._safe_widget_operation(safe_update)
        if not self.is_destroyed:
            self.update_id = self.after(40, self._update_camera_frame)

    def _animate_live_indicator(self):
        """Güvenli canlı indikatör animasyonu."""
        def safe_animate():
            try:
                if self.is_destroyed or not self.winfo_exists():
                    return
                for camera_id in self.fps_vars:
                    canvas, indicator = self.live_indicators[camera_id]
                    if self.system_running:
                        color = self.colors['danger'] if time.time() % 1.2 < 0.6 else self.colors['primary']
                        canvas.itemconfig(indicator, fill=color)
                    else:
                        canvas.itemconfig(indicator, fill=self.colors['border'])
            except tk.TclError as e:
                if "invalid command name" in str(e):
                    self.is_destroyed = True
                    return
                logging.error(f"Live indicator animasyon hatası: {e}")
            except Exception as e:
                logging.error(f"Live indicator animasyon hatası: {e}")

        self._safe_widget_operation(safe_animate)
        if not self.is_destroyed:
            self.after(350, self._animate_live_indicator)

    def _pulse_status_indicator(self):
        """Güvenli durum göstergesi nabız animasyonu."""
        def safe_pulse():
            try:
                if self.is_destroyed or not self.winfo_exists():
                    return
                if self.system_running:
                    self.pulse_value = (self.pulse_value + 1) % 20
                    color_val = int(255 - 30 * abs(math.sin(self.pulse_value / 6.28)))
                    self.status_canvas.itemconfig(self.status_indicator, fill=f'#{color_val:02x}c8{83:02x}')
                else:
                    self.status_canvas.itemconfig(self.status_indicator, fill=self.colors['danger'])
            except tk.TclError as e:
                if "invalid command name" in str(e):
                    self.is_destroyed = True
                    return
                logging.error(f"Pulse animasyon hatası: {e}")
            except Exception as e:
                logging.error(f"Pulse animasyon hatası: {e}")

        self._safe_widget_operation(safe_pulse)
        if not self.is_destroyed:
            self.after(120, self._pulse_status_indicator)

    # ============================= Olay ve Popup Yönetimi =============================

    def update_system_status(self, running):
        """Güvenli sistem durumu güncelleme."""
        def safe_status_update():
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

        self._safe_widget_operation(safe_status_update)

    def _show_fall_alert(self):
        """Düşme algılandığında pop-up ve sesli uyarı gösterir."""
        def safe_alert():
            try:
                if self.is_destroyed or not self.winfo_exists():
                    return
                messagebox.showwarning(
                    "Düşme Algılandı!",
                    f"ID: {self.last_track_id}\n"
                    f"Güven: {self.last_detection_confidence:.2f}\n"
                    f"Zaman: {self.last_detection_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                # Sesli uyarı
                try:
                    winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
                except Exception as e:
                    logging.warning(f"Sesli uyarı hatası: {e}")
            except tk.TclError as e:
                if "invalid command name" in str(e):
                    self.is_destroyed = True
                logging.error(f"Uyarı gösterim hatası: {e}")
            except Exception as e:
                logging.error(f"Uyarı gösterim hatası: {e}")

        self._safe_widget_operation(safe_alert)

    def _export_event_image(self):
        """Olay görüntüsünü masaüstüne kaydeder."""
        if self.last_frames.get(self.current_camera_id):
            now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fall_event_{now}.jpg"
            path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
            cv2.imwrite(path, self.last_frames[self.current_camera_id])
            messagebox.showinfo("Kayıt Başarılı", f"Görüntü başarıyla kaydedildi:\n{path}")

    def _show_event_details(self):
        """Düşme olayının detaylarını popup ile gösterir."""
        if self.last_detection_time:
            messagebox.showinfo(
                "Olay Detayı",
                f"Düşme Olayı\n"
                f"ID: {self.last_track_id}\n"
                f"Güven: {self.last_detection_confidence:.2f}\n"
                f"Zaman: {self.last_detection_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            messagebox.showinfo("Olay Detayı", "Henüz düşme olayı algılanmadı.")

    def on_destroy(self):
        """Frame yok edilirken çağrılır."""
        try:
            self.is_destroyed = True
            self._cleanup_resources()
        except Exception as e:
            logging.error(f"Dashboard destroy hatası: {e}")

    def destroy(self):
        """Widget'ı güvenli şekilde yok eder."""
        try:
            self.on_destroy()
            super().destroy()
        except Exception as e:
            logging.error(f"Dashboard destroy hatası: {e}")

    def _toggle_system(self):
        """Sistemi başlat/durdur butonu için çağrılır."""
        try:
            if not self.system_running:
                self.start_fn()
            else:
                self.stop_fn()
        except Exception as e:
            logging.error(f"Sistem başlatılırken/durdurulurken hatası: {str(e)}")
            messagebox.showerror("Hata", "Sistem başlatılamadı veya durdurulamadı.")

    def _on_camera_select(self, event=None):
        """Kamera seçildiğinde çağrılır."""
        selected_id = self.camera_var.get()
        if selected_id in [f"camera_{cam.camera_index}" for cam in self.cameras]:
            self.current_camera_id = selected_id
            logging.info(f"Kamera seçildi: {self.selected_id}")

    def _start_animations(self):
        """Tüm animasyonları başlatır."""
        """
        Tüm animasyon fonksiyonlarını başlatır: buton nabzı, canlı indikatör, durum göstergesi.
        """
        self._animate_button_pulse()
        self._animate_live_indicator()
        self._pulse_status_indicator()
