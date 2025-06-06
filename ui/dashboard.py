# =======================================================================================
# 📄 Dosya Adı: dashboard.py (ULTRA ENHANCED VERSION)
# 📁 Konum: guard_pc_app/ui/dashboard.py
# 📌 Açıklama:
# YOLOv11 Pose Estimation + DeepSORT tabanlı ultra gelişmiş dashboard UI.
# Tam ekran desteği, çoklu kamera grid görünümü, performans optimizasyonları
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
import queue

class DashboardFrame(tk.Frame):
    """
    Ultra gelişmiş YOLOv11 Pose Estimation + DeepSORT dashboard arayüzü.
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
        self.is_fullscreen = False
        self.current_view_mode = "grid"  # "grid" veya "single"
        self.selected_camera_index = 0
        self.frame_queue = queue.Queue(maxsize=2)  # Frame kuyruğu
        self.processing_thread = None
        
        # Performans optimizasyonu için
        self.frame_skip_counter = 0
        self.frame_skip_rate = 2  # Her 2 frame'de 1 işle
        self.last_update_time = time.time()
        self.target_fps = 30
        self.min_update_interval = 1.0 / self.target_fps
        
        # Frame buffer'ları
        self.frame_buffers = {f"camera_{cam.camera_index}": None for cam in cameras}
        self.processed_frames = {f"camera_{cam.camera_index}": None for cam in cameras}
        self.frame_locks = {f"camera_{cam.camera_index}": threading.Lock() for cam in cameras}
        
        # UI elementleri için değişkenler
        self.camera_frames = {}
        self.camera_labels = {}
        self.fps_labels = {}
        self.status_labels = {}
        
        self.last_detection_time = None
        self.last_detection_confidence = 0.0
        self.last_track_id = None
        self.update_id = None
        self.is_destroyed = False
        
        # Tracking istatistikleri
        self.active_tracks = {}
        self.fall_events_history = deque(maxlen=50)
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

        # Tracking bilgileri için değişkenler
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
        
        # İşleme thread'ini başlat
        self._start_processing_thread()
        
        # Kamera güncellemelerini başlat
        self._start_camera_updates()

    def load_icons(self):
        """Gerekli ikonları yükler."""
        self.icons = {}
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")
        icons_to_load = [
            "settings", "history", "logout", "start", "stop", "user", "camera", 
            "alert", "logo", "fullscreen", "grid", "single", "exit_fullscreen"
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
        """Eksik ikonlar için yer tutucu oluşturur."""
        img = Image.new('RGBA', (24, 24), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        if name == "fullscreen":
            draw.rectangle([4, 4, 20, 20], outline=self.colors['primary'], width=2)
            draw.rectangle([8, 8, 16, 16], outline=self.colors['primary'], width=1)
        elif name == "grid":
            for i in range(2):
                for j in range(2):
                    x, y = 4 + i * 9, 4 + j * 9
                    draw.rectangle([x, y, x + 7, y + 7], outline=self.colors['primary'], width=1)
        else:
            draw.ellipse([2, 2, 22, 22], outline=self.colors['primary'], width=2)
        
        self.icons[name] = ImageTk.PhotoImage(img)

    def _create_ui(self):
        """Ana UI yapısını oluşturur."""
        self.configure(bg=self.colors['light'])
        
        # Ana container
        self.main_container = tk.Frame(self, bg=self.colors['light'])
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Grid layout
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=4)
        self.main_container.rowconfigure(0, weight=0)
        self.main_container.rowconfigure(1, weight=1)
        
        # Header
        self._create_header()
        
        # Sol panel (kontroller)
        self._create_left_panel()
        
        # Sağ panel (kameralar)
        self._create_camera_panel()

    def _create_header(self):
        """Üst başlık çubuğunu oluşturur."""
        header = tk.Canvas(self.main_container, height=60, highlightthickness=0)
        self._draw_gradient(header, self.colors['gradient_start'], self.colors['gradient_end'])
        header.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Logo ve başlık
        logo_frame = tk.Frame(header, bg=self.colors['primary'])
        logo_frame.place(x=20, y=10)
        
        if "logo" in self.icons:
            tk.Label(logo_frame, image=self.icons["logo"], bg=self.colors['primary']).pack(side=tk.LEFT, padx=5)
        
        tk.Label(logo_frame, text="Guard AI - YOLOv11", font=("Segoe UI", 18, "bold"), 
                fg="white", bg=self.colors['primary']).pack(side=tk.LEFT)

        # Sağ üst kontroller
        controls_frame = tk.Frame(header, bg=self.colors['primary'])
        controls_frame.place(relx=1, x=-20, y=15, anchor="ne")
        
        # Görünüm modları
        view_frame = tk.Frame(controls_frame, bg=self.colors['primary'])
        view_frame.pack(side=tk.LEFT, padx=10)
        
        # Grid görünümü
        self.grid_btn = tk.Button(view_frame, text="⊞ Grid", font=("Segoe UI", 10),
                                 bg=self.colors['info'], fg="white", bd=0,
                                 command=lambda: self._set_view_mode("grid"),
                                 padx=10, pady=5, cursor="hand2")
        self.grid_btn.pack(side=tk.LEFT, padx=2)
        
        # Tekli görünüm
        self.single_btn = tk.Button(view_frame, text="◻ Tekli", font=("Segoe UI", 10),
                                   bg=self.colors['secondary'], fg="white", bd=0,
                                   command=lambda: self._set_view_mode("single"),
                                   padx=10, pady=5, cursor="hand2")
        self.single_btn.pack(side=tk.LEFT, padx=2)
        
        # Tam ekran butonu
        self.fullscreen_btn = tk.Button(controls_frame, text="⛶ Tam Ekran", font=("Segoe UI", 10),
                                       bg=self.colors['success'], fg="white", bd=0,
                                       command=self._toggle_fullscreen,
                                       padx=15, pady=5, cursor="hand2")
        self.fullscreen_btn.pack(side=tk.LEFT, padx=10)
        
        # Kullanıcı bilgisi
        user_frame = tk.Frame(controls_frame, bg=self.colors['primary'])
        user_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(user_frame, text=self.user.get('displayName', 'Kullanıcı'),
                font=("Segoe UI", 12), fg="white", bg=self.colors['primary']).pack()
        
        # Çıkış
        tk.Button(controls_frame, text="Çıkış", font=("Segoe UI", 10),
                 bg=self.colors['danger'], fg="white", bd=0,
                 command=self.logout_fn, padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT)

    def _create_left_panel(self):
        """Sol kontrol panelini oluşturur."""
        left_panel = tk.Frame(self.main_container, bg=self.colors['light'], width=300)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        left_panel.grid_propagate(False)
        
        # Sistem kontrolü
        control_card = self._create_card(left_panel, "Sistem Kontrolü")
        control_card.pack(fill=tk.X, pady=(0, 10))
        
        # Başlat/Durdur butonu
        self.control_var = tk.StringVar(value="Sistemi Başlat")
        self.control_button = tk.Button(control_card, textvariable=self.control_var,
                                       font=("Segoe UI", 14, "bold"),
                                       bg=self.colors['success'], fg="white",
                                       command=self._toggle_system,
                                       relief=tk.FLAT, pady=10, cursor="hand2")
        self.control_button.pack(fill=tk.X, padx=10, pady=10)
        
        # Durum göstergesi
        self.status_var = tk.StringVar(value="Sistem Kapalı")
        status_label = tk.Label(control_card, textvariable=self.status_var,
                               font=("Segoe UI", 12), bg=self.colors['card'])
        status_label.pack(pady=5)
        
        # İstatistikler
        stats_card = self._create_card(left_panel, "İstatistikler")
        stats_card.pack(fill=tk.X, pady=(0, 10))
        
        stats_grid = tk.Frame(stats_card, bg=self.colors['card'])
        stats_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # İstatistik satırları
        for i, (key, label) in enumerate([
            ('active_tracks', 'Aktif Takip'),
            ('total_detections', 'Toplam Tespit'),
            ('fall_alerts', 'Düşme Uyarısı')
        ]):
            row_frame = tk.Frame(stats_grid, bg=self.colors['card'])
            row_frame.pack(fill=tk.X, pady=2)
            
            tk.Label(row_frame, text=f"{label}:", font=("Segoe UI", 11),
                    bg=self.colors['card']).pack(side=tk.LEFT)
            
            tk.Label(row_frame, textvariable=self.tracking_info_vars[key],
                    font=("Segoe UI", 11, "bold"), fg=self.colors['primary'],
                    bg=self.colors['card']).pack(side=tk.RIGHT)
        
        # Son olay
        event_card = self._create_card(left_panel, "Son Düşme Olayı")
        event_card.pack(fill=tk.X, pady=(0, 10))
        
        event_info = tk.Frame(event_card, bg=self.colors['card'])
        event_info.pack(fill=tk.X, padx=10, pady=10)
        
        for var in [self.event_time_var, self.event_conf_var, self.event_id_var]:
            tk.Label(event_info, textvariable=var, font=("Segoe UI", 10),
                    bg=self.colors['card']).pack(anchor=tk.W, pady=2)
        
        # Hızlı erişim
        menu_card = self._create_card(left_panel, "Menü")
        menu_card.pack(fill=tk.BOTH, expand=True)
        
        menu_buttons = [
            ("Ayarlar", self.settings_fn, self.colors['info']),
            ("Geçmiş", self.history_fn, self.colors['info'])
        ]
        
        for text, cmd, color in menu_buttons:
            btn = tk.Button(menu_card, text=text, font=("Segoe UI", 11),
                           bg=self.colors['card'], fg=color,
                           relief=tk.FLAT, command=cmd,
                           cursor="hand2", anchor="w", padx=20, pady=8)
            btn.pack(fill=tk.X, padx=10, pady=2)

    def _create_camera_panel(self):
        """Kamera görüntüleme panelini oluşturur."""
        self.camera_panel = tk.Frame(self.main_container, bg=self.colors['dark'])
        self.camera_panel.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=10)
        
        # Başlangıçta grid görünümü
        self._create_grid_view()

    def _create_grid_view(self):
        """Grid görünümünü oluşturur."""
        # Mevcut içeriği temizle
        for widget in self.camera_panel.winfo_children():
            widget.destroy()
        
        # Kamera sayısına göre grid boyutunu belirle
        num_cameras = len(self.cameras)
        if num_cameras <= 1:
            rows, cols = 1, 1
        elif num_cameras <= 2:
            rows, cols = 1, 2
        elif num_cameras <= 4:
            rows, cols = 2, 2
        elif num_cameras <= 6:
            rows, cols = 2, 3
        else:
            rows, cols = 3, 3
        
        # Grid konfigürasyonu
        for i in range(rows):
            self.camera_panel.rowconfigure(i, weight=1)
        for j in range(cols):
            self.camera_panel.columnconfigure(j, weight=1)
        
        # Her kamera için frame oluştur
        for idx, camera in enumerate(self.cameras):
            if idx >= rows * cols:
                break
                
            row = idx // cols
            col = idx % cols
            camera_id = f"camera_{camera.camera_index}"
            
            # Kamera frame
            cam_frame = tk.Frame(self.camera_panel, bg=self.colors['dark'], 
                                highlightbackground=self.colors['border'],
                                highlightthickness=2)
            cam_frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            
            # Başlık
            header = tk.Frame(cam_frame, bg=self.colors['info'], height=30)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            
            # Kamera adı
            cam_name = tk.Label(header, text=f"Kamera {camera.camera_index}",
                               font=("Segoe UI", 10, "bold"), fg="white",
                               bg=self.colors['info'])
            cam_name.pack(side=tk.LEFT, padx=10)
            
            # FPS göstergesi
            fps_label = tk.Label(header, text="0 FPS", font=("Segoe UI", 9),
                                fg="white", bg=self.colors['info'])
            fps_label.pack(side=tk.RIGHT, padx=10)
            self.fps_labels[camera_id] = fps_label
            
            # Durum göstergesi
            status_label = tk.Label(header, text="●", font=("Segoe UI", 12),
                                   fg=self.colors['danger'], bg=self.colors['info'])
            status_label.pack(side=tk.RIGHT, padx=5)
            self.status_labels[camera_id] = status_label
            
            # Görüntü alanı
            img_frame = tk.Frame(cam_frame, bg="#000000")
            img_frame.pack(fill=tk.BOTH, expand=True)
            
            # Görüntü etiketi
            img_label = tk.Label(img_frame, bg="#000000", cursor="hand2")
            img_label.pack(fill=tk.BOTH, expand=True)
            
            # Tıklama ile tam ekrana geç
            img_label.bind("<Double-Button-1>", lambda e, idx=idx: self._show_single_camera(idx))
            
            self.camera_labels[camera_id] = img_label
            self.camera_frames[camera_id] = cam_frame

    def _create_single_view(self, camera_index):
        """Tekli kamera görünümünü oluşturur."""
        # Mevcut içeriği temizle
        for widget in self.camera_panel.winfo_children():
            widget.destroy()
        
        camera = self.cameras[camera_index]
        camera_id = f"camera_{camera.camera_index}"
        
        # Ana frame
        main_frame = tk.Frame(self.camera_panel, bg=self.colors['dark'])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Üst kontrol çubuğu
        control_bar = tk.Frame(main_frame, bg=self.colors['info'], height=40)
        control_bar.pack(fill=tk.X)
        control_bar.pack_propagate(False)
        
        # Geri butonu
        back_btn = tk.Button(control_bar, text="◀ Geri", font=("Segoe UI", 10),
                            bg=self.colors['secondary'], fg="white", bd=0,
                            command=lambda: self._set_view_mode("grid"),
                            padx=15, pady=5, cursor="hand2")
        back_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Kamera seçici
        cam_select_frame = tk.Frame(control_bar, bg=self.colors['info'])
        cam_select_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(cam_select_frame, text="Kamera:", font=("Segoe UI", 11),
                fg="white", bg=self.colors['info']).pack(side=tk.LEFT, padx=5)
        
        # Kamera listesi
        cam_names = [f"Kamera {cam.camera_index}" for cam in self.cameras]
        cam_var = tk.StringVar(value=cam_names[camera_index])
        cam_menu = ttk.Combobox(cam_select_frame, textvariable=cam_var,
                               values=cam_names, state="readonly", width=15)
        cam_menu.pack(side=tk.LEFT)
        cam_menu.bind("<<ComboboxSelected>>", 
                     lambda e: self._show_single_camera(cam_menu.current()))
        
        # Bilgi göstergeleri
        info_frame = tk.Frame(control_bar, bg=self.colors['info'])
        info_frame.pack(side=tk.RIGHT, padx=20)
        
        # FPS
        fps_label = tk.Label(info_frame, text="0 FPS", font=("Segoe UI", 11, "bold"),
                            fg="white", bg=self.colors['info'])
        fps_label.pack(side=tk.LEFT, padx=10)
        self.fps_labels[camera_id] = fps_label
        
        # Durum
        status_label = tk.Label(info_frame, text="● Bağlantı Yok", 
                               font=("Segoe UI", 11), fg=self.colors['danger'],
                               bg=self.colors['info'])
        status_label.pack(side=tk.LEFT, padx=10)
        self.status_labels[camera_id] = status_label
        
        # Görüntü alanı
        img_frame = tk.Frame(main_frame, bg="#000000")
        img_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Görüntü etiketi
        img_label = tk.Label(img_frame, bg="#000000")
        img_label.pack(fill=tk.BOTH, expand=True)
        
        self.camera_labels[camera_id] = img_label
        self.camera_frames[camera_id] = main_frame

    def _set_view_mode(self, mode):
        """Görünüm modunu değiştirir."""
        self.current_view_mode = mode
        
        if mode == "grid":
            self._create_grid_view()
            self.grid_btn.config(bg=self.colors['primary'])
            self.single_btn.config(bg=self.colors['secondary'])
        else:  # single
            self._create_single_view(self.selected_camera_index)
            self.grid_btn.config(bg=self.colors['secondary'])
            self.single_btn.config(bg=self.colors['primary'])

    def _show_single_camera(self, index):
        """Belirli bir kamerayı tekli görünümde gösterir."""
        self.selected_camera_index = index
        self._set_view_mode("single")

    def _toggle_fullscreen(self):
        """Tam ekran modunu açar/kapatır."""
        root = self.winfo_toplevel()
        
        if not self.is_fullscreen:
            # Tam ekrana geç
            self.is_fullscreen = True
            root.attributes('-fullscreen', True)
            self.fullscreen_btn.config(text="◱ Normal")
            
            # Sol paneli gizle
            for widget in self.main_container.grid_slaves():
                if int(widget.grid_info()["column"]) == 0 and int(widget.grid_info()["row"]) == 1:
                    widget.grid_remove()
            
            # Kamera panelini genişlet
            self.camera_panel.grid(column=0, columnspan=2)
            
        else:
            # Normal moda dön
            self.is_fullscreen = False
            root.attributes('-fullscreen', False)
            self.fullscreen_btn.config(text="⛶ Tam Ekran")
            
            # Sol paneli göster
            for widget in self.main_container.grid_slaves():
                widget.grid()
            
            # Grid düzenini düzelt
            self._create_ui()

    def _create_card(self, parent, title):
        """Kart bileşeni oluşturur."""
        card = tk.Frame(parent, bg=self.colors['card'], 
                       highlightbackground=self.colors['border'],
                       highlightthickness=1)
        
        # Başlık
        title_label = tk.Label(card, text=title, font=("Segoe UI", 12, "bold"),
                              bg=self.colors['card'], fg=self.colors['text'])
        title_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        return card

    def _draw_gradient(self, canvas, start_color, end_color):
        """Gradient arka plan çizer."""
        width = 1920  # Maksimum genişlik
        height = 60
        
        r1, g1, b1 = self._hex_to_rgb(start_color)
        r2, g2, b2 = self._hex_to_rgb(end_color)
        
        for i in range(width):
            ratio = i / width
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            canvas.create_line(i, 0, i, height, fill=color)

    def _hex_to_rgb(self, hex_color):
        """Hex renk kodunu RGB'ye çevirir."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _start_processing_thread(self):
        """Frame işleme thread'ini başlatır."""
        self.processing_thread = threading.Thread(target=self._process_frames, daemon=True)
        self.processing_thread.start()

    def _process_frames(self):
        """Arka planda frame işleme - optimize edilmiş."""
        fall_detector = FallDetector.get_instance()
        
        while not self.is_destroyed:
            try:
                if not self.system_running:
                    time.sleep(0.1)
                    continue
                
                # Frame skip kontrolü
                self.frame_skip_counter += 1
                if self.frame_skip_counter % self.frame_skip_rate != 0:
                    continue
                
                # Her kamera için işlem
                for camera in self.cameras:
                    if not camera.is_running:
                        continue
                        
                    camera_id = f"camera_{camera.camera_index}"
                    
                    # Frame al
                    frame = camera.get_frame()
                    if frame is None:
                        continue
                    
                    # Frame'i buffer'a kaydet
                    with self.frame_locks[camera_id]:
                        self.frame_buffers[camera_id] = frame.copy()
                    
                    # Sadece seçili kamera için YOLOv11 işleme
                    if (self.current_view_mode == "single" and 
                        camera.camera_index == self.cameras[self.selected_camera_index].camera_index):
                        
                        # YOLOv11 Pose Estimation
                        annotated_frame, tracks = fall_detector.get_detection_visualization(frame)
                        
                        # Tracking istatistiklerini güncelle
                        self.tracking_stats['active_tracks'] = len(tracks)
                        if tracks:
                            self.tracking_stats['total_detections'] += len(tracks)
                        
                        # Düşme algılama
                        is_fall, confidence, track_id = fall_detector.detect_fall(frame, tracks)
                        
                        if is_fall and confidence > 0.6:
                            self._handle_fall_detection(camera_id, confidence, track_id)
                        
                        # İşlenmiş frame'i kaydet
                        with self.frame_locks[camera_id]:
                            self.processed_frames[camera_id] = annotated_frame
                    
                    # Grid modunda basit tespit
                    elif self.current_view_mode == "grid":
                        # Sadece bounding box tespiti (daha hızlı)
                        results = fall_detector.model.predict(frame, conf=0.5, classes=[0], verbose=False)
                        
                        simple_frame = frame.copy()
                        if results and len(results) > 0 and results[0].boxes is not None:
                            boxes = results[0].boxes.xyxy.cpu().numpy()
                            for box in boxes:
                                x1, y1, x2, y2 = map(int, box)
                                cv2.rectangle(simple_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        
                        with self.frame_locks[camera_id]:
                            self.processed_frames[camera_id] = simple_frame
                
                # FPS kontrolü
                time.sleep(0.01)  # CPU yükünü azalt
                
            except Exception as e:
                logging.error(f"Frame işleme hatası: {e}")
                time.sleep(0.1)

    def _start_camera_updates(self):
        """Kamera güncellemelerini başlatır."""
        self._update_camera_displays()

    def _update_camera_displays(self):
        """Kamera görüntülerini günceller - optimize edilmiş."""
        if self.is_destroyed:
            return
        
        current_time = time.time()
        
        # Minimum güncelleme aralığı kontrolü
        if current_time - self.last_update_time < self.min_update_interval:
            self.update_id = self.after(10, self._update_camera_displays)
            return
        
        self.last_update_time = current_time
        
        try:
            # Her kamera için görüntüyü güncelle
            for camera_id, label in self.camera_labels.items():
                if camera_id not in self.frame_locks:
                    continue
                
                # İşlenmiş frame varsa onu kullan, yoksa ham frame
                frame = None
                with self.frame_locks[camera_id]:
                    if camera_id in self.processed_frames and self.processed_frames[camera_id] is not None:
                        frame = self.processed_frames[camera_id]
                    elif camera_id in self.frame_buffers and self.frame_buffers[camera_id] is not None:
                        frame = self.frame_buffers[camera_id]
                
                if frame is None:
                    continue
                
                # Frame boyutlandırma
                if self.current_view_mode == "grid":
                    # Grid modunda daha küçük
                    display_width = label.winfo_width() or 400
                    display_height = label.winfo_height() or 300
                else:
                    # Tekli modda büyük
                    display_width = label.winfo_width() or 1200
                    display_height = label.winfo_height() or 800
                
                if display_width > 1 and display_height > 1:
                    # Aspect ratio'yu koru
                    h, w = frame.shape[:2]
                    aspect = w / h
                    
                    if display_width / display_height > aspect:
                        new_height = display_height
                        new_width = int(new_height * aspect)
                    else:
                        new_width = display_width
                        new_height = int(new_width / aspect)
                    
                    # Resize
                    resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                    
                    # PIL Image'e çevir
                    frame_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(frame_rgb)
                    
                    # Parlaklık ayarı
                    enhancer = ImageEnhance.Brightness(pil_img)
                    pil_img = enhancer.enhance(1.1)
                    
                    # Tkinter PhotoImage
                    tk_img = ImageTk.PhotoImage(pil_img)
                    
                    # Label'ı güncelle
                    label.configure(image=tk_img)
                    label.image = tk_img
                
                # FPS ve durum güncellemeleri
                camera_index = int(camera_id.split('_')[1])
                if camera_index < len(self.cameras):
                    camera = self.cameras[camera_index]
                    
                    # FPS
                    if camera_id in self.fps_labels:
                        self.fps_labels[camera_id].config(text=f"{int(camera.fps)} FPS")
                    
                    # Durum
                    if camera_id in self.status_labels:
                        if self.system_running and camera.is_running:
                            self.status_labels[camera_id].config(text="● Aktif", fg=self.colors['success'])
                        else:
                            self.status_labels[camera_id].config(text="● Kapalı", fg=self.colors['danger'])
            
            # İstatistikleri güncelle
            self._update_stats()
            
        except Exception as e:
            logging.error(f"Görüntü güncelleme hatası: {e}")
        
        # Sonraki güncelleme
        self.update_id = self.after(33, self._update_camera_displays)  # ~30 FPS

    def _update_stats(self):
        """İstatistikleri günceller."""
        try:
            self.tracking_info_vars['active_tracks'].set(str(self.tracking_stats['active_tracks']))
            self.tracking_info_vars['total_detections'].set(str(self.tracking_stats['total_detections']))
            self.tracking_info_vars['fall_alerts'].set(str(self.tracking_stats['fall_alerts']))
        except Exception as e:
            logging.error(f"İstatistik güncelleme hatası: {e}")

    def _handle_fall_detection(self, camera_id, confidence, track_id):
        """Düşme algılandığında çağrılır."""
        try:
            now = datetime.datetime.now()
            self.last_detection_time = now
            self.last_detection_confidence = confidence
            self.last_track_id = track_id
            
            # İstatistikleri güncelle
            self.tracking_stats['fall_alerts'] += 1
            
            # UI güncellemeleri
            self.event_time_var.set(f"Zaman: {now.strftime('%H:%M:%S')}")
            self.event_conf_var.set(f"Güven: {confidence:.3f}")
            self.event_id_var.set(f"ID: {track_id}")
            
            # Sesli uyarı
            threading.Thread(target=lambda: winsound.PlaySound("SystemExclamation", 
                                                              winsound.SND_ALIAS), 
                           daemon=True).start()
            
            logging.info(f"Düşme algılandı! Kamera: {camera_id}, ID: {track_id}, Güven: {confidence:.3f}")
            
        except Exception as e:
            logging.error(f"Düşme algılama işleme hatası: {e}")

    def _toggle_system(self):
        """Sistemi başlatır/durdurur."""
        if not self.system_running:
            self.start_fn()
        else:
            self.stop_fn()

    def update_system_status(self, running):
        """Sistem durumunu günceller."""
        self.system_running = running
        
        if running:
            self.status_var.set("🟢 Sistem Aktif")
            self.control_var.set("Sistemi Durdur")
            self.control_button.config(bg=self.colors['danger'])
        else:
            self.status_var.set("🔴 Sistem Kapalı")
            self.control_var.set("Sistemi Başlat")
            self.control_button.config(bg=self.colors['success'])

    def update_fall_detection(self, screenshot, confidence, event_data):
        """Düşme algılama sonucunu günceller."""
        # Ana thread'de güncelleme yap
        self.after(0, lambda: self._handle_fall_detection(
            event_data.get('camera_id', 'unknown'),
            confidence,
            event_data.get('track_id', 'N/A')
        ))

    def _on_widget_destroy(self, event):
        """Widget yok edildiğinde."""
        if event.widget == self:
            self.is_destroyed = True
            self._cleanup_resources()

    def _cleanup_resources(self):
        """Kaynakları temizler."""
        try:
            # Update timer'ı durdur
            if hasattr(self, 'update_id') and self.update_id:
                self.after_cancel(self.update_id)
                self.update_id = None
            
            # Processing thread'i durdur
            self.is_destroyed = True
            
            logging.info("Dashboard kaynakları temizlendi")
        except Exception as e:
            logging.error(f"Kaynak temizleme hatası: {e}")

    def on_destroy(self):
        """Frame yok edilirken çağrılır."""
        self.is_destroyed = True
        self._cleanup_resources()

    def destroy(self):
        """Widget'ı güvenli şekilde yok eder."""
        try:
            self.on_destroy()
            super().destroy()
        except Exception as e:
            logging.error(f"Dashboard destroy hatası: {e}")