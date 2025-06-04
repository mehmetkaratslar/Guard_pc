# =======================================================================================
# 📄 Dosya Adı: dashboard.py (ENHANCED VERSION)
# 📁 Konum: guard_pc_app/ui/dashboard.py
# 📌 Açıklama:
# YOLOv11 Pose Estimation + DeepSORT tabanlı gelişmiş dashboard UI.
# Real-time pose visualization, tracking ID'ler, düşme algılama göstergeleri.
# Gelişmiş görselleştirme ve interaktif kontroller.
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
from collections import deque
from core.fall_detection import FallDetector

class DashboardFrame(tk.Frame):
    """
    Gelişmiş YOLOv11 Pose Estimation + DeepSORT dashboard arayüzü.
    """

    def __init__(self, parent, user, cameras, start_fn, stop_fn, settings_fn, history_fn, logout_fn):
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
        
        # Yeni eklenen değişkenler
        self.active_tracks = {}  # {track_id: track_info}
        self.fall_events_history = deque(maxlen=50)  # Son 50 düşme olayı
        self.pose_visualization_enabled = True
        self.tracking_stats = {
            'total_detections': 0,
            'active_tracks': 0,
            'fall_alerts': 0,
            'session_start': time.time()
        }
        
        self.bind("<Destroy>", self._on_widget_destroy)

        # Renk teması
        self.colors = {
            'primary': "#3420ED", 'secondary': "#FF6B81", 'success': "#38B2AC",
            'warning': "#F6AD55", 'danger': "#E53E3E", 'info': "#3182CE",
            'dark': "#1A202C", 'light': "#F7FAFC", 'card': "#FFFFFF",
            'text': "#1A202C", 'text_secondary': "#718096", 'border': "#E2E8F0",
            'highlight': "#EDF2F7", 'gradient_start': "#B794F4", 'gradient_end': "#6B46C1",
            'pose_point': "#FF4081", 'skeleton_line': "#4CAF50", 'tracking_box': "#2196F3"
        }

        # Kamera durumları
        self.current_camera_id = f"camera_{cameras[0].camera_index}" if cameras else None
        self.frame_locks = {f"camera_{cam.camera_index}": threading.Lock() for cam in cameras}
        self.camera_labels = {}
        self.fps_vars = {f"camera_{cam.camera_index}": tk.StringVar(value="0 FPS") for cam in cameras}
        self.live_indicators = {}

        # Tracking ve pose bilgileri için değişkenler
        self.tracking_info_vars = {
            'active_tracks': tk.StringVar(value="0"),
            'total_detections': tk.StringVar(value="0"),
            'fall_alerts': tk.StringVar(value="0"),
            'pose_points': tk.StringVar(value="0")
        }

        # Son düşme olayı değişkenleri
        self.event_time_var = tk.StringVar(value="Zaman: -")
        self.event_conf_var = tk.StringVar(value="Güven: -")
        self.event_id_var = tk.StringVar(value="ID: -")
        self.event_pose_var = tk.StringVar(value="Pose: -")

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
            "camera_select", "pose_points", "tracking", "statistics"
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
        
        if name == "pose_points":
            # Pose noktaları ikonu
            for i, (x, y) in enumerate([(8, 6), (16, 6), (8, 12), (16, 12), (12, 18)]):
                draw.ellipse([x-2, y-2, x+2, y+2], fill=color)
        elif name == "tracking":
            # Tracking ikonu
            draw.rectangle([4, 4, 20, 20], outline=color, width=2)
            draw.line([8, 8, 16, 16], fill=color, width=2)
        elif name == "statistics":
            # İstatistik ikonu
            draw.rectangle([4, 16, 8, 20], fill=color)
            draw.rectangle([10, 12, 14, 20], fill=color)
            draw.rectangle([16, 8, 20, 20], fill=color)
        else:
            # Varsayılan ikon
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
        """Gradient uyumlu modern mavi-mor başlık çubuğu."""
        gradient_bg = "#1B22FA"  # Gradientle uyumlu mor-mavi tonu

        header = tk.Canvas(self, height=80, highlightthickness=0, bg=gradient_bg)
        self._draw_gradient(header, self.colors['gradient_start'], self.colors['gradient_end'], width=2000, height=80)
        header.grid(row=0, column=0, columnspan=2, sticky="new")
        header.create_rectangle(0, 78, 2000, 80, fill="#1A1A1A", outline="")

        # Sol: Logo ve Uygulama Adı
        logo_frame = tk.Frame(header, bg=gradient_bg, bd=0, highlightthickness=0)
        logo_frame.place(relx=0, rely=0.5, x=25, anchor="w")
        if "logo" in self.icons:
            tk.Label(logo_frame, image=self.icons["logo"], bg=gradient_bg).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(
            logo_frame, text="Guard AI",
            font=("Poppins", 22, "bold"), fg="#BBFFFA", bg=gradient_bg
        ).pack(side=tk.LEFT)

        # Orta: Sistem Durumu
        status_frame = tk.Frame(header, bg=gradient_bg)
        status_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            status_frame, text="YOLOv11 Pose + DeepSORT",
            font=("Segoe UI", 13, "bold"), fg="#BBFFFA", bg=gradient_bg
        ).pack()

        tracks_info = tk.Frame(status_frame, bg=gradient_bg)
        tracks_info.pack()
        tk.Label(tracks_info, text="Aktif Takip: ", font=("Segoe UI", 11), fg="#FFD700", bg=gradient_bg).pack(side=tk.LEFT)
        tk.Label(tracks_info, textvariable=self.tracking_info_vars['active_tracks'],
                font=("Segoe UI", 11, "bold"), fg="#00FF7F", bg=gradient_bg).pack(side=tk.LEFT)

        # Sağ: Ayarlar, Geçmiş, Kullanıcı, Çıkış
        top_right_panel = tk.Frame(header, bg=gradient_bg)
        top_right_panel.place(relx=1, rely=0.5, x=-25, anchor="e")

        # Ayarlar Butonu
        settings_btn = tk.Button(
            top_right_panel, font=("Poppins", 12, "bold"),
            bg="#74b9ff", fg="#000000", relief=tk.FLAT,
            padx=10, pady=6, command=self.settings_fn,
            activebackground="#0984e3", activeforeground="#ffffff", cursor="hand2"
        )
        if "settings" in self.icons:
            settings_btn.config(image=self.icons["settings"], compound=tk.LEFT, padx=10)
        settings_btn.pack(side=tk.LEFT, padx=5)

        # Geçmiş Butonu
        history_btn = tk.Button(
            top_right_panel, image=self.icons.get("history", None),
            bg=gradient_bg, relief=tk.FLAT,
            activebackground="#6c5ce7", cursor="hand2",
            command=self.history_fn
        )
        history_btn.pack(side=tk.LEFT, padx=5)

        # Kullanıcı adı ve çıkış
        user_frame = tk.Frame(top_right_panel, bg=gradient_bg)
        user_frame.pack(side=tk.LEFT, padx=10)
        if "user" in self.icons:
            tk.Label(user_frame, image=self.icons["user"], bg=gradient_bg).pack(side=tk.LEFT, padx=8)
        tk.Label(
            user_frame, text=self.user.get('displayName', 'Kullanıcı'),
            font=("Poppins", 14, "bold"), fg="#BBFFFA", bg=gradient_bg
        ).pack(side=tk.LEFT, padx=10)

        # Çıkış butonu
        logout_btn = tk.Button(
            top_right_panel, text="Çıkış Yap", font=("Poppins", 12, "bold"),
            bg="#d63031", fg="#BBFFFA", relief=tk.FLAT,
            padx=15, pady=6, command=self.logout_fn,
            activebackground="#c0392b", activeforeground="#ffffff", cursor="hand2",
            bd=0, highlightthickness=0, compound=tk.LEFT
        )
        if "logout" in self.icons:
            logout_btn.config(image=self.icons["logout"], padx=10)

        logout_btn.bind("<Enter>", lambda e: logout_btn.config(bg="#e74c3c"))
        logout_btn.bind("<Leave>", lambda e: logout_btn.config(bg="#d63031"))
        logout_btn.pack(side=tk.LEFT, padx=5)



        # Logo çerçevesi
        logo_frame = tk.Frame(header, bg=self.colors['light'], bd=0, highlightthickness=0)
        logo_frame.place(relx=0, rely=0.5, x=25, anchor="w")
        if "logo" in self.icons:
            tk.Label(logo_frame, image=self.icons["logo"], bg=self.colors['light']).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(
            logo_frame, text="Guard AI",
            font=("Poppins", 22, "bold"), fg="#645353", bg=self.colors['light']
        ).pack(side=tk.LEFT)

        # Orta panel - sistem durumu
        status_frame = tk.Frame(header, bg=self.colors['light'])
        status_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(
            status_frame, text="YOLOv11 Pose + DeepSORT",
            font=("Segoe UI", 13, "bold"), fg="#000000", bg=self.colors['light']
        ).pack()

        tracks_info = tk.Frame(status_frame, bg=self.colors['light'])
        tracks_info.pack()
        tk.Label(tracks_info, text="Aktif Takip: ", 
                font=("Segoe UI", 11), fg="#FFD700", bg=self.colors['light']).pack(side=tk.LEFT)
        tk.Label(tracks_info, textvariable=self.tracking_info_vars['active_tracks'],
                font=("Segoe UI", 11, "bold"), fg="#00FF7F", bg=self.colors['light']).pack(side=tk.LEFT)

        # Sağ üst panel
        top_right_panel = tk.Frame(header, bg=self.colors['light'])
        top_right_panel.place(relx=1, rely=0.5, x=-25, anchor="e")

        # Ayarlar Butonu
        settings_btn = tk.Button(
            top_right_panel, font=("Poppins", 12, "bold"),
            bg=self.colors['info'], fg="#000000", relief=tk.FLAT,
            padx=10, pady=6, command=self.settings_fn,
            activebackground="#1E88E5", activeforeground="#3c4de6", cursor="hand2"
        )
        if "settings" in self.icons:
            settings_btn.config(image=self.icons["settings"], compound=tk.LEFT, padx=10)
        settings_btn.pack(side=tk.LEFT, padx=5)

        # Geçmiş Butonu
        history_btn = tk.Button(
            top_right_panel, image=self.icons.get("history", None),
            bg=self.colors['light'], relief=tk.FLAT,
            activebackground=self.colors['secondary'], cursor="hand2",
            command=self.history_fn
        )
        history_btn.pack(side=tk.LEFT, padx=5)

        # Kullanıcı ve çıkış
        user_frame = tk.Frame(top_right_panel, bg=self.colors['light'])
        user_frame.pack(side=tk.LEFT, padx=10)
        if "user" in self.icons:
            tk.Label(user_frame, image=self.icons["user"], bg=self.colors['light']).pack(side=tk.LEFT, padx=8)
        tk.Label(
            user_frame, text=self.user.get('displayName', 'Kullanıcı'),
            font=("Poppins", 14, "bold"), fg="#061AEC", bg=self.colors['light']
        ).pack(side=tk.LEFT, padx=10)

        logout_btn = tk.Button(
            top_right_panel, text="Çıkış Yap", font=("Poppins", 12, "bold"),
            bg=self.colors['danger'], fg="#ffffff", relief=tk.FLAT,
            padx=15, pady=6, command=self.logout_fn,
            activebackground="#B71C1C", activeforeground="#fd0505", cursor="hand2",
            bd=0, highlightthickness=0, compound=tk.LEFT
        )
        if "logout" in self.icons:
            logout_btn.config(image=self.icons["logout"], padx=10)

        logout_btn.bind("<Enter>", lambda e: logout_btn.config(bg="#E53935"))
        logout_btn.bind("<Leave>", lambda e: logout_btn.config(bg=self.colors['danger']))
        logout_btn.pack(side=tk.LEFT, padx=5)















    def _create_left_panel(self):
        """Gelişmiş kontrol paneli."""
        left_panel = tk.Frame(self, bg=self.colors['light'])
        left_panel.grid(row=1, column=0, sticky="nsew", padx=25, pady=25)
        left_panel.columnconfigure(0, weight=1)

        # Sistem kontrol kartı
        control_card = self._create_neuromorphic_card(left_panel, "AI Düşme Algılama Kontrolü")
        control_card.pack(fill=tk.BOTH, pady=(0, 15))

        # Model bilgileri
        model_info_frame = tk.Frame(control_card, bg=self.colors['card'])
        model_info_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(model_info_frame, text="🧠 YOLOv11 Pose Estimation", 
                font=("Helvetica", 11, "bold"), fg=self.colors['info'], 
                bg=self.colors['card']).pack(anchor=tk.W)
        tk.Label(model_info_frame, text="🎯 DeepSORT Multi-Object Tracking", 
                font=("Helvetica", 11, "bold"), fg=self.colors['info'], 
                bg=self.colors['card']).pack(anchor=tk.W)

        # Kamera seçimi
        camera_select_frame = tk.Frame(control_card, bg=self.colors['card'])
        camera_select_frame.pack(fill=tk.X, pady=8)
        tk.Label(
            camera_select_frame, text="📹 Kamera:", font=("Helvetica", 12, "bold"),
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

        # Gelişmiş durum göstergesi
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
            font=("Helvetica", 14, "bold"), fg=self.colors['danger'], bg=self.colors['card'], padx=8
        ).pack(side=tk.LEFT)

        # Başlat/Durdur butonu
        button_frame = tk.Frame(control_card, bg=self.colors['card'], padx=12, pady=12)
        button_frame.pack(fill=tk.X)
        
        self.control_var = tk.StringVar(value="AI Sistemi Başlat")
        self.control_button = tk.Button(
            button_frame, textvariable=self.control_var, font=("Helvetica", 14, "bold"),
            bg=self.colors['success'], fg="#ffffff", relief=tk.FLAT,
            padx=20, pady=12, command=self._toggle_system,
            activebackground="#2C7A7B", activeforeground="#ffffff", cursor="hand2"
        )
        if "start" in self.icons:
            self.control_button.config(image=self.icons["start"], compound=tk.LEFT, padx=12)
        self.control_button.pack(fill=tk.X)

        # Tracking istatistikleri kartı
        stats_card = self._create_neuromorphic_card(left_panel, "📊 Takip İstatistikleri")
        stats_card.pack(fill=tk.BOTH, pady=(0, 15))
        
        # İstatistik grid'i
        stats_grid = tk.Frame(stats_card, bg=self.colors['card'])
        stats_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # 2x2 grid
        for i, (key, label, icon) in enumerate([
            ('active_tracks', 'Aktif Takip', '🎯'),
            ('total_detections', 'Toplam Tespit', '👥'),
            ('fall_alerts', 'Düşme Uyarısı', '⚠️'),
            ('pose_points', 'Pose Noktası', '🔘')
        ]):
            row, col = i // 2, i % 2
            
            stat_frame = tk.Frame(stats_grid, bg=self.colors['card'], padx=8, pady=8)
            stat_frame.grid(row=row, column=col, sticky="ew", padx=5, pady=5)
            stats_grid.columnconfigure(col, weight=1)
            
            tk.Label(stat_frame, text=icon, font=("Helvetica", 14), 
                    bg=self.colors['card']).pack()
            tk.Label(stat_frame, textvariable=self.tracking_info_vars[key], 
                    font=("Helvetica", 16, "bold"), fg=self.colors['primary'], 
                    bg=self.colors['card']).pack()
            tk.Label(stat_frame, text=label, font=("Helvetica", 9), 
                    fg=self.colors['text_secondary'], bg=self.colors['card']).pack()

        # Son Düşme Olayı kartı (geliştirilmiş)
        event_card = self._create_neuromorphic_card(left_panel, "🚨 Son Düşme Olayı")
        event_card.pack(fill=tk.BOTH, pady=(0, 15))
        
        for var, icon in [(self.event_time_var, "🕐"), (self.event_conf_var, "📊"), 
                         (self.event_id_var, "🆔"), (self.event_pose_var, "🤸")]:
            event_info_frame = tk.Frame(event_card, bg=self.colors['card'])
            event_info_frame.pack(fill=tk.X, padx=12, pady=2)
            tk.Label(event_info_frame, text=icon, font=("Helvetica", 12), 
                    bg=self.colors['card']).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(event_info_frame, textvariable=var, font=("Arial", 11),
                    fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT)

        # Pose görselleştirme kontrolü
        pose_control_frame = tk.Frame(event_card, bg=self.colors['card'])
        pose_control_frame.pack(fill=tk.X, padx=12, pady=8)
        
        self.pose_viz_var = tk.BooleanVar(value=True)
        pose_check = tk.Checkbutton(
            pose_control_frame, text="Pose Noktalarını Göster",
            variable=self.pose_viz_var, font=("Helvetica", 10),
            bg=self.colors['card'], fg=self.colors['text'],
            command=self._toggle_pose_visualization
        )
        pose_check.pack(anchor=tk.W)

        # Menü kartı
        menu_card = self._create_neuromorphic_card(left_panel, "📋 Menü")
        menu_card.pack(fill=tk.BOTH)
        
        for text, cmd, icon_name, color in [
            ("Ayarlar", self.settings_fn, "settings", self.colors['info']),
            ("Olay Geçmişi", self.history_fn, "history", self.colors['info']),
            ("İstatistikler", self._show_detailed_stats, "statistics", self.colors['info'])
        ]:
            btn_container = tk.Frame(menu_card, bg=self.colors['card'], pady=4)
            btn_container.pack(fill=tk.X)
            btn = tk.Button(
                btn_container, text=text, font=("Helvetica", 11, "bold"),
                bg=self.colors['card'], fg=color, relief=tk.FLAT,
                padx=20, pady=8, command=cmd,
                activebackground=self.colors['highlight'], activeforeground=color,
                cursor="hand2", anchor="w"
            )
            if icon_name in self.icons:
                btn.config(image=self.icons[icon_name], compound=tk.LEFT, padx=12)
            btn.pack(fill=tk.X)

    def _create_right_panel(self):
        """Gelişmiş kamera görüntü paneli."""
        right_panel = tk.Frame(self, bg=self.colors['light'])
        right_panel.grid(row=1, column=1, sticky="nsew", padx=20, pady=25)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)

        camera_card = self._create_neuromorphic_card(right_panel, "🎥 Canlı AI Görüntü Analizi")
        camera_card.pack(fill=tk.BOTH, expand=True)

        # Gelişmiş kontrol paneli
        control_panel = tk.Frame(camera_card, bg=self.colors['card'])
        control_panel.pack(fill=tk.X, padx=16, pady=(16, 8))
        
        # Sol kontroller
        left_controls = tk.Frame(control_panel, bg=self.colors['card'])
        left_controls.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(left_controls, text="🤖 AI Modülleri:", font=("Helvetica", 11, "bold"),
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.ai_modules_var = tk.StringVar(value="YOLOv11 + DeepSORT Aktif")
        tk.Label(left_controls, textvariable=self.ai_modules_var, font=("Helvetica", 10),
                fg=self.colors['success'], bg=self.colors['card']).pack(side=tk.LEFT)

        # Sağ kontroller
        right_controls = tk.Frame(control_panel, bg=self.colors['card'])
        right_controls.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Görüntü ayarları
        tk.Button(right_controls, text="🎛️", font=("Helvetica", 12),
                 bg=self.colors['card'], fg=self.colors['text'], relief=tk.FLAT,
                 command=self._show_camera_settings, cursor="hand2").pack(side=tk.RIGHT, padx=2)
        
        tk.Button(right_controls, text="📸", font=("Helvetica", 12),
                 bg=self.colors['card'], fg=self.colors['text'], relief=tk.FLAT,
                 command=self._capture_screenshot, cursor="hand2").pack(side=tk.RIGHT, padx=2)

        # Sekme paneli
        notebook = ttk.Notebook(camera_card)
        notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 16))

        # Her kamera için gelişmiş sekme
        for camera in self.cameras:
            camera_id = f"camera_{camera.camera_index}"
            tab = tk.Frame(notebook, bg=self.colors['card'])
            notebook.add(tab, text=f"📹 Kamera {camera.camera_index}")
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=0)
            tab.rowconfigure(1, weight=1)

            # Gelişmiş durum çubuğu
            status_bar = tk.Frame(tab, bg=self.colors['card'], padx=12, pady=8)
            status_bar.pack(fill=tk.X)
            
            # Sol durum bilgileri
            left_status = tk.Frame(status_bar, bg=self.colors['card'])
            left_status.pack(side=tk.LEFT, fill=tk.Y)
            
            live_frame = tk.Frame(left_status, bg=self.colors['card'])
            live_frame.pack(side=tk.LEFT)
            live_canvas = tk.Canvas(live_frame, width=10, height=10, bg=self.colors['card'], highlightthickness=0)
            live_canvas.pack(side=tk.LEFT)
            live_indicator = live_canvas.create_oval(1, 1, 9, 9, fill=self.colors['danger'], outline="")
            tk.Label(
                live_frame, text="🔴 CANLI", font=("Helvetica", 11, "bold"),
                fg=self.colors['danger'], bg=self.colors['card']
            ).pack(side=tk.LEFT, padx=5)
            
            # FPS ve model bilgisi
            tk.Label(
                left_status, textvariable=self.fps_vars[camera_id], font=("Helvetica", 11),
                fg=self.colors['text_secondary'], bg=self.colors['card']
            ).pack(side=tk.LEFT, padx=15)
            
            # Sağ durum bilgileri
            right_status = tk.Frame(status_bar, bg=self.colors['card'])
            right_status.pack(side=tk.RIGHT, fill=tk.Y)
            
            tk.Label(right_status, text="🧠 AI: YOLOv11", font=("Helvetica", 9),
                    fg=self.colors['info'], bg=self.colors['card']).pack(side=tk.RIGHT, padx=5)

            # Kamera ekranı
            camera_display = tk.Frame(tab, bg="#000000", width=820, height=600)
            camera_display.pack(padx=16, pady=16, expand=True)
            camera_display.pack_propagate(False)
            
            # Overlay frame (pose points ve tracking info için)
            overlay_frame = tk.Frame(camera_display, bg="#000000")
            overlay_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            
            camera_label = tk.Label(overlay_frame, bg="#000000")
            camera_label.pack(expand=True, fill=tk.BOTH)
            
            self.camera_labels[camera_id] = camera_label
            self.live_indicators[camera_id] = (live_canvas, live_indicator)

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
            canvas.create_rectangle(i * width / steps, 0, (i + 1) * width / steps, height, fill=color, outline="")
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
        
        title_frame = tk.Frame(card, bg=self.colors['card'])
        title_frame.pack(fill=tk.X, pady=(0, 14))
        
        tk.Label(
            title_frame, text=title, font=("Helvetica", 16, "bold"),
            fg=self.colors['primary'], bg=self.colors['card']
        ).pack(side=tk.LEFT)
        
        return card

    def _start_camera_updates(self):
        """Gelişmiş kamera güncelleyici başlatır."""
        if self.update_id is not None:
            self.after_cancel(self.update_id)
        self._update_camera_frame()

    def _update_camera_frame(self):
        """Gelişmiş YOLOv11 Pose + DeepSORT kamera güncellemesi."""
        def safe_update():
            try:
                if self.is_destroyed or not self.winfo_exists():
                    return

                fall_detector = FallDetector.get_instance()
                total_pose_points = 0
                active_tracks_count = 0
                
                for camera in self.cameras:
                    camera_id = f"camera_{camera.camera_index}"
                    if self.system_running and camera.is_running:
                        frame = camera.get_frame()
                        if frame is not None and frame.size > 0:
                            with self.frame_locks[camera_id]:
                                self.last_frames[camera_id] = frame.copy()

                            # YOLOv11 Pose Estimation + DeepSORT tracking
                            annotated_frame, tracks = fall_detector.get_detection_visualization(frame)
                            
                            # Tracking istatistiklerini güncelle
                            active_tracks_count += len(tracks)
                            self.tracking_stats['active_tracks'] = active_tracks_count
                            self.tracking_stats['total_detections'] += len(tracks)
                            
                            # Pose noktalarını say
                            for track in tracks:
                                track_id = track.get('track_id')
                                if track_id in fall_detector.person_tracks:
                                    person_track = fall_detector.person_tracks[track_id]
                                    if person_track.has_valid_pose():
                                        valid_keypoints = np.sum(
                                            person_track.latest_keypoint_confs > 0.3
                                        ) if person_track.latest_keypoint_confs is not None else 0
                                        total_pose_points += valid_keypoints

                            # Düşme algılama kontrolü
                            is_fall, confidence, track_id = fall_detector.detect_fall(frame, tracks)
                            if is_fall and confidence > 0.5:
                                now = datetime.datetime.now()
                                self.last_detection_time = now
                                self.last_detection_confidence = confidence
                                self.last_track_id = track_id
                                
                                # UI değişkenlerini güncelle
                                self.event_time_var.set(f"🕐 {now.strftime('%H:%M:%S')}")
                                self.event_conf_var.set(f"📊 {confidence:.3f}")
                                self.event_id_var.set(f"🆔 {track_id}")
                                
                                # Pose analizi bilgisi
                                if track_id in fall_detector.person_tracks:
                                    person_track = fall_detector.person_tracks[track_id]
                                    if person_track.has_valid_pose():
                                        valid_poses = np.sum(person_track.latest_keypoint_confs > 0.3)
                                        self.event_pose_var.set(f"🤸 {valid_poses}/17 nokta")
                                
                                self.tracking_stats['fall_alerts'] += 1
                                
                                # Fall event history'e ekle
                                self.fall_events_history.append({
                                    'time': now,
                                    'confidence': confidence,
                                    'track_id': track_id,
                                    'pose_points': total_pose_points
                                })
                                
                                logging.info(f"🚨 YOLOv11 DÜŞME ALGILANDI: ID={track_id}, Güven={confidence:.3f}")
                                self._show_fall_alert()

                            # Görüntüyü güncelle - Enhanced visualization
                            if self.pose_visualization_enabled:
                                # Pose noktaları ve skeleton çizimini içeren frame kullan
                                display_frame = annotated_frame
                            else:
                                # Sadece bounding box'ları olan frame kullan
                                display_frame = self._draw_simple_boxes(frame, tracks)
                            
                            frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                            pil_img = Image.fromarray(frame_rgb)
                            pil_img = ImageEnhance.Brightness(pil_img).enhance(1.09)
                            pil_img = pil_img.resize((820, 600), Image.LANCZOS)
                            tk_img = ImageTk.PhotoImage(pil_img)

                            if not self.is_destroyed and self.winfo_exists():
                                self.camera_labels[camera_id].configure(image=tk_img)
                                self.camera_labels[camera_id].image = tk_img
                                self.fps_vars[camera_id].set(f"{int(camera.fps)} FPS")
                    else:
                        # Kamera çalışmıyorsa siyah ekran göster
                        if camera_id in self.camera_labels:
                            black_frame = np.zeros((600, 820, 3), dtype=np.uint8)
                            if not self.system_running:
                                cv2.putText(black_frame, "Sistem Durduruldu", (200, 300),
                                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                            else:
                                cv2.putText(black_frame, "Kamera Bağlanıyor...", (200, 300),
                                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                            
                            pil_img = Image.fromarray(black_frame)
                            tk_img = ImageTk.PhotoImage(pil_img)
                            self.camera_labels[camera_id].configure(image=tk_img)
                            self.camera_labels[camera_id].image = tk_img

                # İstatistikleri güncelle
                self._update_tracking_stats(active_tracks_count, total_pose_points)
                
            except tk.TclError as e:
                if "invalid command name" in str(e):
                    self.is_destroyed = True
                    return
                logging.error(f"Kamera güncelleme hatası: {e}")
            except Exception as e:
                logging.error(f"Kamera güncelleme hatası: {e}")

        self._safe_widget_operation(safe_update)
        if not self.is_destroyed:
            self.update_id = self.after(33, self._update_camera_frame)  # ~30 FPS

    def _draw_simple_boxes(self, frame, tracks):
        """Sadece bounding box'ları çizer (pose points olmadan)."""
        annotated_frame = frame.copy()
        for track in tracks:
            track_id = track.get('track_id')
            bbox = track.get('bbox', [0, 0, 100, 100])
            confidence = track.get('confidence', 0.0)
            
            x1, y1, x2, y2 = bbox
            color = (0, 255, 0)  # Yeşil
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            label = f"ID: {track_id}"
            if confidence > 0:
                label += f" ({confidence:.2f})"
            
            cv2.putText(annotated_frame, label, (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        return annotated_frame

    def _update_tracking_stats(self, active_tracks, pose_points):
        """Tracking istatistiklerini günceller."""
        try:
            self.tracking_info_vars['active_tracks'].set(str(active_tracks))
            self.tracking_info_vars['total_detections'].set(str(self.tracking_stats['total_detections']))
            self.tracking_info_vars['fall_alerts'].set(str(self.tracking_stats['fall_alerts']))
            self.tracking_info_vars['pose_points'].set(str(pose_points))
        except Exception as e:
            logging.error(f"İstatistik güncelleme hatası: {e}")

    def _toggle_pose_visualization(self):
        """Pose görselleştirmesini açar/kapatır."""
        self.pose_visualization_enabled = self.pose_viz_var.get()
        logging.info(f"Pose görselleştirme: {'Açık' if self.pose_visualization_enabled else 'Kapalı'}")

    def _show_camera_settings(self):
        """Kamera ayarları dialogunu gösterir."""
        settings_window = tk.Toplevel(self)
        settings_window.title("Kamera Ayarları")
        settings_window.geometry("400x300")
        settings_window.configure(bg=self.colors['card'])
        
        tk.Label(settings_window, text="🎥 Kamera Ayarları", 
                font=("Helvetica", 16, "bold"), bg=self.colors['card']).pack(pady=20)
        
        # Pose detection threshold
        threshold_frame = tk.Frame(settings_window, bg=self.colors['card'])
        threshold_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(threshold_frame, text="Pose Güven Eşiği:", 
                font=("Helvetica", 12), bg=self.colors['card']).pack(anchor=tk.W)
        
        threshold_var = tk.DoubleVar(value=0.3)
        threshold_scale = tk.Scale(threshold_frame, from_=0.1, to=0.9, resolution=0.1,
                                  variable=threshold_var, orient=tk.HORIZONTAL,
                                  bg=self.colors['card'])
        threshold_scale.pack(fill=tk.X, pady=5)
        
        # Fall detection sensitivity
        sensitivity_frame = tk.Frame(settings_window, bg=self.colors['card'])
        sensitivity_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(sensitivity_frame, text="Düşme Hassaslığı:", 
                font=("Helvetica", 12), bg=self.colors['card']).pack(anchor=tk.W)
        
        sensitivity_var = tk.DoubleVar(value=0.6)
        sensitivity_scale = tk.Scale(sensitivity_frame, from_=0.3, to=0.9, resolution=0.1,
                                    variable=sensitivity_var, orient=tk.HORIZONTAL,
                                    bg=self.colors['card'])
        sensitivity_scale.pack(fill=tk.X, pady=5)
        
        def apply_settings():
            try:
                fall_detector = FallDetector.get_instance()
                fall_detector.fall_detection_params['confidence_threshold'] = threshold_var.get()
                # Hassaslık ayarını uygula (örnek)
                messagebox.showinfo("Başarılı", "Ayarlar uygulandı!")
                settings_window.destroy()
            except Exception as e:
                messagebox.showerror("Hata", f"Ayarlar uygulanırken hata: {str(e)}")
        
        tk.Button(settings_window, text="Uygula", command=apply_settings,
                 bg=self.colors['primary'], fg="white", font=("Helvetica", 12),
                 pady=8).pack(pady=20)

    def _capture_screenshot(self):
        """Ekran görüntüsü alır."""
        try:
            if self.current_camera_id and self.current_camera_id in self.last_frames:
                frame = self.last_frames[self.current_camera_id]
                if frame is not None:
                    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"guard_screenshot_{now}.jpg"
                    path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
                    cv2.imwrite(path, frame)
                    messagebox.showinfo("Başarılı", f"Ekran görüntüsü kaydedildi:\n{path}")
                else:
                    messagebox.showwarning("Uyarı", "Kaydedilecek görüntü bulunamadı!")
            else:
                messagebox.showwarning("Uyarı", "Aktif kamera bulunamadı!")
        except Exception as e:
            messagebox.showerror("Hata", f"Ekran görüntüsü alınırken hata: {str(e)}")

    def _show_detailed_stats(self):
        """Detaylı istatistikleri gösterir."""
        stats_window = tk.Toplevel(self)
        stats_window.title("Detaylı İstatistikler")
        stats_window.geometry("500x400")
        stats_window.configure(bg=self.colors['card'])
        
        tk.Label(stats_window, text="📊 Sistem İstatistikleri", 
                font=("Helvetica", 16, "bold"), bg=self.colors['card']).pack(pady=20)
        
        # Temel istatistikler
        basic_frame = tk.LabelFrame(stats_window, text="Temel İstatistikler", 
                                   font=("Helvetica", 12, "bold"), bg=self.colors['card'])
        basic_frame.pack(fill=tk.X, padx=20, pady=10)
        
        session_time = time.time() - self.tracking_stats['session_start']
        stats_text = [
            f"Oturum Süresi: {int(session_time//3600):02d}:{int((session_time%3600)//60):02d}:{int(session_time%60):02d}",
            f"Toplam Tespit: {self.tracking_stats['total_detections']}",
            f"Düşme Uyarısı: {self.tracking_stats['fall_alerts']}",
            f"Aktif Takip: {self.tracking_stats['active_tracks']}"
        ]
        
        for stat in stats_text:
            tk.Label(basic_frame, text=stat, font=("Helvetica", 11), 
                    bg=self.colors['card']).pack(anchor=tk.W, padx=10, pady=2)
        
        # Model bilgileri
        model_frame = tk.LabelFrame(stats_window, text="Model Bilgileri", 
                                   font=("Helvetica", 12, "bold"), bg=self.colors['card'])
        model_frame.pack(fill=tk.X, padx=20, pady=10)
        
        try:
            fall_detector = FallDetector.get_instance()
            model_info = fall_detector.get_model_info()
            
            model_stats = [
                f"Model: {model_info.get('model_name', 'N/A')}",
                f"Cihaz: {model_info.get('device', 'N/A')}",
                f"Güven Eşiği: {model_info.get('confidence_threshold', 'N/A')}",
                f"Keypoint Sayısı: {model_info.get('keypoints_count', 'N/A')}"
            ]
            
            for stat in model_stats:
                tk.Label(model_frame, text=stat, font=("Helvetica", 11), 
                        bg=self.colors['card']).pack(anchor=tk.W, padx=10, pady=2)
        except:
            tk.Label(model_frame, text="Model bilgisi alınamadı", 
                    font=("Helvetica", 11), bg=self.colors['card']).pack(padx=10, pady=10)

    def _show_fall_alert(self):
        """Düşme uyarısını gösterir."""
        def safe_alert():
            try:
                if self.is_destroyed or not self.winfo_exists():
                    return
                
                # Görsel uyarı
                messagebox.showwarning(
                    "🚨 DÜŞME ALGILANDI!",
                    f"YOLOv11 Pose Estimation ile düşme tespit edildi!\n\n"
                    f"📍 Takip ID: {self.last_track_id}\n"
                    f"📊 Güven Skoru: {self.last_detection_confidence:.3f}\n"
                    f"🕐 Zaman: {self.last_detection_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_detection_time else 'N/A'}\n\n"
                    f"Lütfen durumu kontrol edin!"
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

    def update_system_status(self, running):
        """Sistem durumunu günceller."""
        def safe_status_update():
            self.system_running = running
            if running:
                self.status_var.set("🤖 AI Sistem Aktif")
                self.status_canvas.itemconfig(self.status_indicator, fill=self.colors['success'])
                self.control_var.set("AI Sistemi Durdur")
                self.control_button.config(bg=self.colors['danger'])
                self.ai_modules_var.set("YOLOv11 + DeepSORT Aktif")
                if "stop" in self.icons:
                    self.control_button.config(image=self.icons["stop"])
            else:
                self.status_var.set("Sistem Durduruldu")
                self.status_canvas.itemconfig(self.status_indicator, fill=self.colors['danger'])
                self.control_var.set("AI Sistemi Başlat")
                self.control_button.config(bg=self.colors['success'])
                self.ai_modules_var.set("Sistem Kapalı")
                if "start" in self.icons:
                    self.control_button.config(image=self.icons["start"])

        self._safe_widget_operation(safe_status_update)

    def update_fall_detection(self, screenshot, confidence, event_data):
        """Düşme algılama sonucunu UI'da günceller."""
        def safe_update():
            try:
                if self.is_destroyed or not self.winfo_exists():
                    return
                
                # Son düşme olayı bilgilerini güncelle
                now = datetime.datetime.now()
                self.event_time_var.set(f"🕐 {now.strftime('%H:%M:%S')}")
                self.event_conf_var.set(f"📊 {confidence:.3f}")
                self.event_id_var.set(f"🆔 {event_data.get('id', 'N/A')}")
                
                # Pose analizi varsa ekle
                if 'pose_analysis' in event_data:
                    pose_info = event_data['pose_analysis']
                    self.event_pose_var.set(f"🤸 {pose_info.get('valid_points', 0)}/17 nokta")
                
                # İstatistikleri güncelle
                self.tracking_stats['fall_alerts'] += 1
                self.tracking_info_vars['fall_alerts'].set(str(self.tracking_stats['fall_alerts']))
                
                logging.info("Dashboard düşme algılama bilgileri güncellendi")
                
            except Exception as e:
                logging.error(f"Fall detection UI güncellemesi hatası: {e}")

        self._safe_widget_operation(safe_update)

    def _toggle_system(self):
        """Sistemi başlat/durdur."""
        try:
            if not self.system_running:
                self.start_fn()
            else:
                self.stop_fn()
        except Exception as e:
            logging.error(f"Sistem toggle hatası: {str(e)}")
            messagebox.showerror("Hata", "Sistem başlatılamadı veya durdurulamadı.")

    def _on_camera_select(self, event=None):
        """Kamera seçildiğinde çağrılır."""
        selected_id = self.camera_var.get()
        if selected_id in [f"camera_{cam.camera_index}" for cam in self.cameras]:
            self.current_camera_id = selected_id
            logging.info(f"Kamera seçildi: {selected_id}")

    def _start_animations(self):
        """Animasyonları başlatır."""
        self._animate_live_indicator()
        self._pulse_status_indicator()

    def _animate_live_indicator(self):
        """Canlı indikatör animasyonu."""
        def safe_animate():
            try:
                if self.is_destroyed or not self.winfo_exists():
                    return
                for camera_id in self.fps_vars:
                    if camera_id in self.live_indicators:
                        canvas, indicator = self.live_indicators[camera_id]
                        if self.system_running:
                            color = self.colors['success'] if time.time() % 1.2 < 0.6 else self.colors['primary']
                            canvas.itemconfig(indicator, fill=color)
                        else:
                            canvas.itemconfig(indicator, fill=self.colors['border'])
            except Exception as e:
                logging.error(f"Live indicator animasyon hatası: {e}")

        self._safe_widget_operation(safe_animate)
        if not self.is_destroyed:
            self.after(350, self._animate_live_indicator)

    def _pulse_status_indicator(self):
        """Durum göstergesi nabız animasyonu."""
        def safe_pulse():
            try:
                if self.is_destroyed or not self.winfo_exists():
                    return
                if self.system_running:
                    self.pulse_value = (self.pulse_value + 1) % 20
                    alpha = 0.7 + 0.3 * math.sin(self.pulse_value / 3.14)
                    # Renk değişimi efekti
                    base_color = self.colors['success']
                    # RGB değerlerini al ve alpha uygula
                    r, g, b = self._hex_to_rgb(base_color)
                    r, g, b = int(r*alpha), int(g*alpha), int(b*alpha)
                    pulse_color = f'#{r:02x}{g:02x}{b:02x}'
                    self.status_canvas.itemconfig(self.status_indicator, fill=pulse_color)
                else:
                    self.status_canvas.itemconfig(self.status_indicator, fill=self.colors['danger'])
            except Exception as e:
                logging.error(f"Pulse animasyon hatası: {e}")

        self._safe_widget_operation(safe_pulse)
        if not self.is_destroyed:
            self.after(120, self._pulse_status_indicator)

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

    def _on_widget_destroy(self, event):
        """Widget yok edildiğinde çağrılır."""
        if event.widget == self:
            logging.info("Enhanced Dashboard widget yok ediliyor...")
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
            logging.info("Enhanced Dashboard kaynakları temizlendi")
        except Exception as e:
            logging.error(f"Dashboard kaynak temizleme hatası: {e}")

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