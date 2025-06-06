# =======================================================================================
# 📄 Dosya Adı: dashboard.py (ULTRA ENHANCED VERSION V2 - FIXED)
# 📁 Konum: guard_pc_app/ui/dashboard.py
# 📌 Açıklama:
# Ultra optimize edilmiş dashboard - TEK KAMERA ALANI, hata düzeltmeleri
# Kameralar liste şeklinde seçilir, yüksek performans optimizasyonları
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
    TEK KAMERA ALANI - Kameralar liste halinde seçilir.
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

        # Sistem durumları
        self.system_running = False
        self.is_fullscreen = False
        self.selected_camera_index = 0  # Varsayılan olarak ilk kamera seçili
        
        # Performans optimizasyonu
        self.frame_skip_counter = 0
        self.frame_skip_rate = 1  # Her frame'i işle (daha yüksek kalite)
        self.last_update_time = time.time()
        self.target_fps = 30
        self.min_update_interval = 1.0 / self.target_fps
        
        # Frame yönetimi - TEK KAMERA İÇİN
        self.current_frame = None
        self.processed_frame = None
        self.frame_lock = threading.Lock()
        
        # UI elementleri - TANIMLAMALARI BAŞTA YAPALIM
        self.main_camera_label = None
        self.camera_selector = None
        self.update_id = None
        self.is_destroyed = False
        
        # UI değişkenleri - EKSIK OLANLARI EKLEDIM
        self.camera_info_var = tk.StringVar(value="Kamera seçilmedi")
        self.current_camera_var = tk.StringVar(value="Kamera seçilmedi")
        self.connection_status_var = tk.StringVar(value="🔴 Bağlantı Yok")
        self.fps_display_var = tk.StringVar(value="0 FPS")
        
        # Tracking istatistikleri
        self.tracking_stats = {
            'active_tracks': 0,
            'total_detections': 0,
            'fall_alerts': 0,
            'session_start': time.time(),
            'current_fps': 0
        }
        
        self.bind("<Destroy>", self._on_widget_destroy)

        # Modern dark tema
        self.colors = {
            'bg_primary': "#0D1117",      # GitHub dark background
            'bg_secondary': "#161B22",    # Sidebar background
            'bg_tertiary': "#21262D",     # Card background
            'accent_primary': "#238636",  # Success green
            'accent_danger': "#DA3633",   # Danger red
            'accent_warning': "#FB8500",  # Warning orange
            'accent_info': "#1F6FEB",     # Info blue
            'text_primary': "#F0F6FC",    # Primary text
            'text_secondary': "#8B949E",  # Secondary text
            'border': "#30363D",          # Border color
            'hover': "#30363D"            # Hover effect
        }

        # Tracking bilgileri için değişkenler
        self.tracking_info_vars = {
            'active_tracks': tk.StringVar(value="0"),
            'total_detections': tk.StringVar(value="0"),
            'fall_alerts': tk.StringVar(value="0"),
            'current_fps': tk.StringVar(value="0")
        }

        # Son düşme olayı değişkenleri
        self.event_time_var = tk.StringVar(value="Henüz olay yok")
        self.event_conf_var = tk.StringVar(value="Güven: -")
        self.event_id_var = tk.StringVar(value="ID: -")

        # Kontrol butonları değişkenleri
        self.control_var = tk.StringVar(value="SISTEMI BAŞLAT")
        self.status_var = tk.StringVar(value="🔴 Sistem Kapalı")

        # UI oluştur
        self._create_ultra_modern_ui()
        
        # İşleme thread'ini başlat
        self._start_processing_thread()
        
        # Kamera güncellemelerini başlat
        self._start_camera_updates()

    def _create_ultra_modern_ui(self):
        """Ultra modern UI yapısını oluşturur."""
        self.configure(bg=self.colors['bg_primary'])
        
        # Ana container
        self.main_container = tk.Frame(self, bg=self.colors['bg_primary'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Grid layout - sol panel küçük, sağ panel büyük
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1, minsize=350)  # Sol panel sabit genişlik
        self.main_container.grid_columnconfigure(1, weight=5)  # Kamera alanı çok büyük
        
        # Sol kontrol paneli
        self._create_control_panel()
        
        # Ana kamera alanı (TEK ALAN)
        self._create_single_camera_area()
        
        # Keyboard shortcuts
        self.bind_all("<F11>", lambda e: self.toggle_fullscreen())
        self.bind_all("<Escape>", lambda e: self.exit_fullscreen())
        self.bind_all("<Left>", lambda e: self._previous_camera())
        self.bind_all("<Right>", lambda e: self._next_camera())

    def _create_control_panel(self):
        """Sol kontrol panelini oluşturur."""
        self.control_panel = tk.Frame(self.main_container, bg=self.colors['bg_secondary'], width=350)
        self.control_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.control_panel.grid_propagate(False)
        
        # Scroll edilebilir içerik
        canvas = tk.Canvas(self.control_panel, bg=self.colors['bg_secondary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.control_panel, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_secondary'])
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Header
        self._create_header_section(scrollable_frame)
        
        # Sistem kontrolü
        self._create_system_control_section(scrollable_frame)
        
        # Kamera seçici
        self._create_camera_selector_section(scrollable_frame)
        
        # Canlı istatistikler
        self._create_stats_section(scrollable_frame)
        
        # Son olay bilgisi
        self._create_last_event_section(scrollable_frame)
        
        # Menü butonları
        self._create_menu_section(scrollable_frame)

    def _create_header_section(self, parent):
        """Header section."""
        header_frame = tk.Frame(parent, bg=self.colors['bg_tertiary'], height=100)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        # Logo ve başlık
        title_label = tk.Label(header_frame, text="🛡️ GUARD AI", 
                              font=("Segoe UI", 18, "bold"),
                              fg=self.colors['accent_primary'], bg=self.colors['bg_tertiary'])
        title_label.pack(pady=10)
        
        subtitle_label = tk.Label(header_frame, text="YOLOv11 Düşme Algılama", 
                                 font=("Segoe UI", 11),
                                 fg=self.colors['text_secondary'], bg=self.colors['bg_tertiary'])
        subtitle_label.pack()
        
        # Kullanıcı bilgisi
        user_label = tk.Label(header_frame, text=f"👤 {self.user.get('displayName', 'Kullanıcı')}", 
                             font=("Segoe UI", 10),
                             fg=self.colors['text_primary'], bg=self.colors['bg_tertiary'])
        user_label.pack(pady=(10, 0))

    def _create_system_control_section(self, parent):
        """Sistem kontrolü section."""
        control_frame = tk.LabelFrame(parent, text="🔧 Sistem Kontrolü", 
                                     font=("Segoe UI", 12, "bold"),
                                     fg=self.colors['text_primary'], bg=self.colors['bg_secondary'],
                                     bd=1, relief="solid")
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Ana kontrol butonu
        self.control_button = tk.Button(control_frame, textvariable=self.control_var,
                                       font=("Segoe UI", 14, "bold"),
                                       bg=self.colors['accent_primary'], fg="white",
                                       command=self._toggle_system,
                                       relief=tk.FLAT, pady=15, cursor="hand2",
                                       activebackground=self.colors['hover'])
        self.control_button.pack(fill=tk.X, padx=15, pady=15)
        
        # Sistem durumu
        status_label = tk.Label(control_frame, textvariable=self.status_var,
                               font=("Segoe UI", 12, "bold"), 
                               fg=self.colors['accent_danger'], bg=self.colors['bg_secondary'])
        status_label.pack(pady=(0, 15))
        
        # Tam ekran butonu
        self.fullscreen_button = tk.Button(control_frame, text="🖥️ TAM EKRAN",
                                          font=("Segoe UI", 11, "bold"),
                                          bg=self.colors['accent_info'], fg="white",
                                          command=self.toggle_fullscreen,
                                          relief=tk.FLAT, pady=8, cursor="hand2")
        self.fullscreen_button.pack(fill=tk.X, padx=15, pady=(0, 15))

    def _create_camera_selector_section(self, parent):
        """Kamera seçici section."""
        camera_frame = tk.LabelFrame(parent, text="📹 Kamera Seçimi", 
                                    font=("Segoe UI", 12, "bold"),
                                    fg=self.colors['text_primary'], bg=self.colors['bg_secondary'],
                                    bd=1, relief="solid")
        camera_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Şu anki kamera bilgisi
        current_cam_frame = tk.Frame(camera_frame, bg=self.colors['bg_tertiary'])
        current_cam_frame.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(current_cam_frame, text="Aktif Kamera:", font=("Segoe UI", 10),
                fg=self.colors['text_secondary'], bg=self.colors['bg_tertiary']).pack(anchor="w")
        
        current_camera_label = tk.Label(current_cam_frame, textvariable=self.current_camera_var,
                                       font=("Segoe UI", 12, "bold"),
                                       fg=self.colors['accent_primary'], bg=self.colors['bg_tertiary'])
        current_camera_label.pack(anchor="w", pady=(5, 0))
        
        # Kamera listesi
        tk.Label(camera_frame, text="Kamera Listesi:", font=("Segoe UI", 10),
                fg=self.colors['text_secondary'], bg=self.colors['bg_secondary']).pack(anchor="w", padx=15, pady=(15, 5))
        
        # Kamera butonları
        self.camera_buttons = []
        for i, camera in enumerate(self.cameras):
            btn = tk.Button(camera_frame, text=f"📹 Kamera {camera.camera_index}",
                           font=("Segoe UI", 10), bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'],
                           command=lambda idx=i: self._select_camera(idx),
                           relief=tk.FLAT, pady=8, cursor="hand2",
                           activebackground=self.colors['hover'])
            btn.pack(fill=tk.X, padx=15, pady=2)
            self.camera_buttons.append(btn)
        
        # İlk kamerayı seç (sadece kameralar varsa)
        if self.cameras:
            self._select_camera(0)
        
        # Navigasyon butonları
        nav_frame = tk.Frame(camera_frame, bg=self.colors['bg_secondary'])
        nav_frame.pack(fill=tk.X, padx=15, pady=15)
        
        prev_btn = tk.Button(nav_frame, text="◀ Önceki", font=("Segoe UI", 9),
                            bg=self.colors['accent_info'], fg="white",
                            command=self._previous_camera, relief=tk.FLAT, cursor="hand2")
        prev_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        next_btn = tk.Button(nav_frame, text="Sonraki ▶", font=("Segoe UI", 9),
                            bg=self.colors['accent_info'], fg="white",
                            command=self._next_camera, relief=tk.FLAT, cursor="hand2")
        next_btn.pack(side=tk.RIGHT, padx=(5, 0))

    def _create_stats_section(self, parent):
        """Canlı istatistikler section."""
        stats_frame = tk.LabelFrame(parent, text="📊 Canlı İstatistikler", 
                                   font=("Segoe UI", 12, "bold"),
                                   fg=self.colors['text_primary'], bg=self.colors['bg_secondary'],
                                   bd=1, relief="solid")
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # İstatistik kartları
        stats_data = [
            ('active_tracks', 'Aktif Takip', '👥'),
            ('total_detections', 'Toplam Tespit', '🎯'),
            ('fall_alerts', 'Düşme Uyarısı', '🚨'),
            ('current_fps', 'FPS', '⚡')
        ]
        
        for key, label, icon in stats_data:
            stat_card = tk.Frame(stats_frame, bg=self.colors['bg_tertiary'])
            stat_card.pack(fill=tk.X, padx=15, pady=5)
            
            # İkon ve label
            left_frame = tk.Frame(stat_card, bg=self.colors['bg_tertiary'])
            left_frame.pack(side=tk.LEFT, fill=tk.Y, pady=10, padx=10)
            
            tk.Label(left_frame, text=icon, font=("Segoe UI", 14),
                    bg=self.colors['bg_tertiary']).pack(side=tk.LEFT)
            tk.Label(left_frame, text=label, font=("Segoe UI", 10),
                    fg=self.colors['text_secondary'], bg=self.colors['bg_tertiary']).pack(side=tk.LEFT, padx=(5, 0))
            
            # Değer
            value_label = tk.Label(stat_card, textvariable=self.tracking_info_vars[key],
                                  font=("Segoe UI", 14, "bold"), fg=self.colors['accent_primary'],
                                  bg=self.colors['bg_tertiary'])
            value_label.pack(side=tk.RIGHT, pady=10, padx=10)

    def _create_last_event_section(self, parent):
        """Son olay section."""
        event_frame = tk.LabelFrame(parent, text="🔔 Son Düşme Olayı", 
                                   font=("Segoe UI", 12, "bold"),
                                   fg=self.colors['text_primary'], bg=self.colors['bg_secondary'],
                                   bd=1, relief="solid")
        event_frame.pack(fill=tk.X, padx=10, pady=10)
        
        event_info_frame = tk.Frame(event_frame, bg=self.colors['bg_tertiary'])
        event_info_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Event bilgileri
        for var in [self.event_time_var, self.event_conf_var, self.event_id_var]:
            label = tk.Label(event_info_frame, textvariable=var, font=("Segoe UI", 10),
                           fg=self.colors['text_primary'], bg=self.colors['bg_tertiary'])
            label.pack(anchor="w", pady=2)

    def _create_menu_section(self, parent):
        """Menü section."""
        menu_frame = tk.LabelFrame(parent, text="⚙️ Menü", 
                                  font=("Segoe UI", 12, "bold"),
                                  fg=self.colors['text_primary'], bg=self.colors['bg_secondary'],
                                  bd=1, relief="solid")
        menu_frame.pack(fill=tk.X, padx=10, pady=10)
        
        menu_buttons = [
            ("⚙️ Ayarlar", self.settings_fn, self.colors['accent_info']),
            ("📋 Geçmiş", self.history_fn, self.colors['accent_info']),
            ("🚪 Çıkış", self.logout_fn, self.colors['accent_danger'])
        ]
        
        for text, command, color in menu_buttons:
            btn = tk.Button(menu_frame, text=text, font=("Segoe UI", 11),
                           bg=color, fg="white", command=command,
                           relief=tk.FLAT, cursor="hand2", pady=8)
            btn.pack(fill=tk.X, padx=15, pady=5)

    def _create_single_camera_area(self):
        """TEK KAMERA görüntüleme alanını oluşturur."""
        self.camera_area = tk.Frame(self.main_container, bg=self.colors['bg_primary'])
        self.camera_area.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Kamera info header
        self.camera_header = tk.Frame(self.camera_area, bg=self.colors['bg_tertiary'], height=50)
        self.camera_header.pack(fill=tk.X, padx=10, pady=(10, 5))
        self.camera_header.pack_propagate(False)
        
        # Sol taraf - kamera bilgisi
        left_info = tk.Frame(self.camera_header, bg=self.colors['bg_tertiary'])
        left_info.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=10)
        
        camera_info_label = tk.Label(left_info, textvariable=self.camera_info_var,
                                    font=("Segoe UI", 14, "bold"),
                                    fg=self.colors['accent_primary'], bg=self.colors['bg_tertiary'])
        camera_info_label.pack(anchor="w")
        
        # Sağ taraf - durum bilgileri
        right_info = tk.Frame(self.camera_header, bg=self.colors['bg_tertiary'])
        right_info.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=10)
        
        # Bağlantı durumu
        connection_label = tk.Label(right_info, textvariable=self.connection_status_var,
                                   font=("Segoe UI", 11), fg=self.colors['accent_danger'],
                                   bg=self.colors['bg_tertiary'])
        connection_label.pack(side=tk.LEFT, padx=10)
        
        # FPS bilgisi
        fps_label = tk.Label(right_info, textvariable=self.fps_display_var,
                            font=("Segoe UI", 11, "bold"), fg=self.colors['accent_primary'],
                            bg=self.colors['bg_tertiary'])
        fps_label.pack(side=tk.LEFT, padx=10)
        
        # ANA KAMERA GÖRÜNTÜ ALANI (ÇOK BÜYÜK)
        self.main_camera_frame = tk.Frame(self.camera_area, bg="#000000", highlightthickness=2,
                                         highlightbackground=self.colors['border'])
        self.main_camera_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        # Kamera label'ı
        self.main_camera_label = tk.Label(self.main_camera_frame, bg="#000000", cursor="hand2")
        self.main_camera_label.pack(fill=tk.BOTH, expand=True)
        
        # Double-click tam ekran
        self.main_camera_label.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        
        # İlk placeholder'ı göster
        self._show_camera_placeholder()

    def _show_camera_placeholder(self):
        """Kamera placeholder'ını gösterir."""
        # Büyük placeholder oluştur
        placeholder = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        # Gradient arka plan
        for i in range(720):
            color_intensity = int(20 + (i / 720) * 30)
            placeholder[i, :] = [color_intensity, color_intensity, color_intensity]
        
        # Ana metin
        cv2.putText(placeholder, "GUARD AI", (480, 300), cv2.FONT_HERSHEY_SIMPLEX,
                   3, (56, 134, 54), 4, cv2.LINE_AA)
        cv2.putText(placeholder, "Dusme Algilama Sistemi", (420, 380), cv2.FONT_HERSHEY_SIMPLEX,
                   1.5, (240, 246, 252), 2, cv2.LINE_AA)
        
        # Talimatlar
        cv2.putText(placeholder, "Sol panelden kamera seciniz", (450, 450), cv2.FONT_HERSHEY_SIMPLEX,
                   1, (139, 148, 158), 2, cv2.LINE_AA)
        cv2.putText(placeholder, "Sistemi baslatmak icin 'SISTEMI BASLAT' butonuna tiklayin", (280, 500), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (139, 148, 158), 2, cv2.LINE_AA)
        
        # Klavye kısayolları
        cv2.putText(placeholder, "F11: Tam Ekran | <- ->: Kamera Degistir | ESC: Cikis", (320, 600), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (139, 148, 158), 1, cv2.LINE_AA)
        
        # Çerçeve
        cv2.rectangle(placeholder, (50, 50), (1230, 670), (56, 134, 54), 3)
        
        self._update_main_camera_display(placeholder)



    def _select_camera(self, camera_index):
        """Kamera seçer - GÜNCELLENMIŞ."""
        if 0 <= camera_index < len(self.cameras):
            self.selected_camera_index = camera_index
            camera = self.cameras[camera_index]
            
            # UI güncelle
            self.current_camera_var.set(f"Kamera {camera.camera_index}")
            self.camera_info_var.set(f"📹 Kamera {camera.camera_index}")
            
            # Buton stillerini güncelle
            for i, btn in enumerate(self.camera_buttons):
                if i == camera_index:
                    btn.config(bg=self.colors['accent_primary'], fg="white")
                else:
                    btn.config(bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'])
            
            # Kamera durumunu kontrol et
            if hasattr(camera, 'is_running') and camera.is_running:
                self.connection_status_var.set("🟢 Bağlı")
            else:
                self.connection_status_var.set("🔴 Bağlantı Yok")
            
            logging.info(f"Kamera {camera_index} seçildi")



    def _previous_camera(self):
        """Önceki kameraya geç."""
        if self.cameras:
            new_index = (self.selected_camera_index - 1) % len(self.cameras)
            self._select_camera(new_index)

    def _next_camera(self):
        """Sonraki kameraya geç."""
        if self.cameras:
            new_index = (self.selected_camera_index + 1) % len(self.cameras)
            self._select_camera(new_index)




    def _start_processing_thread(self):
        """Frame işleme thread'ini başlatır - GÜNCELLENMIŞ."""
        self.processing_thread = threading.Thread(target=self._process_frames, daemon=True)
        self.processing_thread.start()
        logging.info("Processing thread başlatıldı")

    def _process_frames(self):
        """TEK KAMERA için optimize edilmiş frame işleme - GÜNCELLENMIŞ."""
        try:
            fall_detector = FallDetector.get_instance()
            logging.info("FallDetector instance alındı")
        except Exception as e:
            logging.error(f"FallDetector başlatma hatası: {e}")
            return
        
        frame_count = 0
        
        while not self.is_destroyed:
            try:
                if not self.system_running or not self.cameras:
                    time.sleep(0.1)
                    continue
                
                # Seçili kameradan frame al
                if self.selected_camera_index < len(self.cameras):
                    camera = self.cameras[self.selected_camera_index]
                    
                    # Kamera çalışıyor mu kontrol et
                    if not hasattr(camera, 'is_running') or not camera.is_running:
                        # Kamerayı başlatmaya çalış
                        try:
                            logging.info(f"Kamera {camera.camera_index} başlatılıyor...")
                            if camera.start():
                                logging.info(f"✅ Kamera {camera.camera_index} başarıyla başlatıldı")
                                self.connection_status_var.set("🟢 Bağlı")
                            else:
                                logging.error(f"❌ Kamera {camera.camera_index} başlatılamadı")
                                self.connection_status_var.set("🔴 Başlatılamadı")
                                time.sleep(1.0)
                                continue
                        except Exception as e:
                            logging.error(f"Kamera başlatma hatası: {e}")
                            self.connection_status_var.set("🔴 Hata")
                            time.sleep(1.0)
                            continue
                    
                    # Frame al
                    frame = camera.get_frame()
                    if frame is None:
                        time.sleep(0.05)
                        continue
                    
                    # Frame'i buffer'a kaydet
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                    
                    try:
                        # YOLOv11 Pose Estimation - Güvenli çağrı
                        annotated_frame, tracks = fall_detector.get_detection_visualization(frame)
                        
                        # İstatistikleri güncelle
                        self.tracking_stats['active_tracks'] = len(tracks) if tracks else 0
                        if tracks:
                            self.tracking_stats['total_detections'] += len(tracks)
                        
                        # FPS hesapla
                        current_time = time.time()
                        if hasattr(self, 'last_fps_time'):
                            fps = 1.0 / (current_time - self.last_fps_time)
                            self.tracking_stats['current_fps'] = int(fps)
                        self.last_fps_time = current_time
                        
                        # Düşme algılama
                        is_fall, confidence, track_id = fall_detector.detect_fall(frame, tracks)
                        
                        if is_fall and confidence > 0.6:
                            self._handle_fall_detection(self.selected_camera_index, confidence, track_id)
                        
                        # İşlenmiş frame'i kaydet
                        with self.frame_lock:
                            self.processed_frame = annotated_frame
                            
                    except Exception as ai_error:
                        logging.warning(f"AI işleme hatası: {ai_error}")
                        # AI hatası durumunda ham frame'i kullan
                        with self.frame_lock:
                            self.processed_frame = frame
                    
                    frame_count += 1
                    
                    # Her 100 frame'de bir log
                    if frame_count % 100 == 0:
                        logging.info(f"İşlenen frame sayısı: {frame_count}")
                
                # CPU yükünü azalt
                time.sleep(0.03)  # ~33 FPS
                
            except Exception as e:
                logging.error(f"Frame işleme hatası: {e}")
                time.sleep(0.1)
        
        logging.info("Frame processing thread sonlandı")




    def _start_camera_updates(self):
        """Kamera güncellemelerini başlatır."""
        self._update_camera_display()

    def _update_camera_display(self):
        """TEK KAMERA görüntüsünü günceller."""
        if self.is_destroyed:
            return
        
        current_time = time.time()
        
        # FPS kontrolü
        if current_time - self.last_update_time < self.min_update_interval:
            self.update_id = self.after(10, self._update_camera_display)
            return
        
        self.last_update_time = current_time
        
        try:
            # Seçili kameradan frame al
            frame = None
            with self.frame_lock:
                if self.processed_frame is not None:
                    frame = self.processed_frame.copy()
                elif self.current_frame is not None:
                    frame = self.current_frame.copy()
            
            if frame is not None:
                # Ana kamera alanının boyutlarını al
                display_width = self.main_camera_label.winfo_width() or 1200
                display_height = self.main_camera_label.winfo_height() or 800
                
                if display_width > 50 and display_height > 50:
                    # Aspect ratio koru
                    h, w = frame.shape[:2]
                    aspect = w / h
                    
                    if display_width / display_height > aspect:
                        new_height = display_height
                        new_width = int(new_height * aspect)
                    else:
                        new_width = display_width
                        new_height = int(new_width / aspect)
                    
                    # Yüksek kalite resize
                    resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                    
                    # Timestamp ekle
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cv2.putText(resized, timestamp, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                               0.8, (0, 255, 136), 2, cv2.LINE_AA)
                    
                    # Kamera bilgisi
                    if self.selected_camera_index < len(self.cameras):
                        camera = self.cameras[self.selected_camera_index]
                        info_text = f"Kamera {camera.camera_index}"
                        cv2.putText(resized, info_text, (20, new_height - 20), cv2.FONT_HERSHEY_SIMPLEX,
                                   0.7, (240, 246, 252), 2, cv2.LINE_AA)
                    
                    self._update_main_camera_display(resized)
            
            # UI bilgilerini güncelle
            self._update_ui_info()
            
        except Exception as e:
            logging.error(f"Kamera display güncelleme hatası: {e}")
        
        # Sonraki güncelleme
        self.update_id = self.after(33, self._update_camera_display)  # ~30 FPS

    def _update_main_camera_display(self, frame):
        """Ana kamera display'ini günceller."""
        try:
            # BGR to RGB
            if len(frame.shape) == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame
            
            # PIL Image
            pil_image = Image.fromarray(frame_rgb)
            
            # Parlaklık ve kontrast ayarı
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(1.05)
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.1)
            
            # PhotoImage
            tk_image = ImageTk.PhotoImage(pil_image)
            
            # Label güncelle
            self.main_camera_label.configure(image=tk_image)
            self.main_camera_label.image = tk_image  # Garbage collection önleme
            
        except Exception as e:
            logging.error(f"Main camera display güncelleme hatası: {e}")

    def _update_ui_info(self):
        """UI bilgilerini günceller."""
        try:
            # İstatistikleri güncelle
            self.tracking_info_vars['active_tracks'].set(str(self.tracking_stats['active_tracks']))
            self.tracking_info_vars['total_detections'].set(str(self.tracking_stats['total_detections']))
            self.tracking_info_vars['fall_alerts'].set(str(self.tracking_stats['fall_alerts']))
            self.tracking_info_vars['current_fps'].set(str(self.tracking_stats['current_fps']))
            
            # Seçili kamera durumu
            if self.selected_camera_index < len(self.cameras):
                camera = self.cameras[self.selected_camera_index]
                
                # Bağlantı durumu
                if self.system_running and camera.is_running:
                    self.connection_status_var.set("🟢 Bağlı")
                    self.fps_display_var.set(f"{self.tracking_stats['current_fps']} FPS")
                else:
                    self.connection_status_var.set("🔴 Bağlantı Yok")
                    self.fps_display_var.set("0 FPS")
            
        except Exception as e:
            logging.error(f"UI info güncelleme hatası: {e}")

    def _handle_fall_detection(self, camera_index, confidence, track_id):
        """Düşme algılandığında çağrılır."""
        try:
            now = datetime.datetime.now()
            
            # İstatistikleri güncelle
            self.tracking_stats['fall_alerts'] += 1
            
            # UI güncellemeleri
            self.event_time_var.set(f"🕐 {now.strftime('%H:%M:%S')}")
            self.event_conf_var.set(f"🎯 Güven: {confidence:.3f}")
            self.event_id_var.set(f"🔍 ID: {track_id}")
            
            # Sesli uyarı
            try:
                threading.Thread(target=lambda: winsound.PlaySound("SystemExclamation", 
                                                                  winsound.SND_ALIAS), 
                               daemon=True).start()
            except:
                pass
            
            # Görsel uyarı
            self._show_fall_alert(confidence)
            
            logging.info(f"🚨 DÜŞME ALGILANDI! Kamera: {camera_index}, ID: {track_id}, Güven: {confidence:.3f}")
            
        except Exception as e:
            logging.error(f"Düşme algılama işleme hatası: {e}")

    def _show_fall_alert(self, confidence):
        """Düşme uyarısı popup'ı gösterir."""
        try:
            # Alert frame oluştur
            alert_frame = tk.Toplevel(self)
            alert_frame.title("🚨 DÜŞME ALGILANDI!")
            alert_frame.geometry("400x200")
            alert_frame.configure(bg=self.colors['accent_danger'])
            alert_frame.transient(self.winfo_toplevel())
            alert_frame.grab_set()
            
            # Alert içeriği
            tk.Label(alert_frame, text="🚨 DÜŞME ALGILANDI!", 
                    font=("Segoe UI", 16, "bold"), fg="white", bg=self.colors['accent_danger']).pack(pady=20)
            
            tk.Label(alert_frame, text=f"Güven Oranı: {confidence:.3f}", 
                    font=("Segoe UI", 12), fg="white", bg=self.colors['accent_danger']).pack()
            
            tk.Label(alert_frame, text=datetime.datetime.now().strftime("Zaman: %H:%M:%S"), 
                    font=("Segoe UI", 12), fg="white", bg=self.colors['accent_danger']).pack(pady=10)
            
            # Kapatma butonu
            tk.Button(alert_frame, text="TAMAM", font=("Segoe UI", 12, "bold"),
                     bg="white", fg=self.colors['accent_danger'],
                     command=alert_frame.destroy, pady=10).pack(pady=20)
            
            # 5 saniye sonra otomatik kapat
            alert_frame.after(5000, alert_frame.destroy)
            
        except Exception as e:
            logging.error(f"Fall alert gösterme hatası: {e}")

    def _toggle_system(self):
        """Sistemi başlatır/durdurur."""
        if not self.system_running:
            self.start_fn()
        else:
            self.stop_fn()

    def toggle_fullscreen(self):
        """Tam ekran modunu açar/kapatır."""
        root = self.winfo_toplevel()
        
        if not self.is_fullscreen:
            # Tam ekrana geç
            self.is_fullscreen = True
            root.attributes('-fullscreen', True)
            
            # Kontrol panelini gizle
            self.control_panel.grid_remove()
            
            # Kamera alanını genişlet
            self.camera_area.grid(column=0, columnspan=2)
            
            # Buton metnini güncelle
            self.fullscreen_button.config(text="🪟 NORMAL EKRAN")
            
            logging.info("Tam ekran moduna geçildi")
            
        else:
            self.exit_fullscreen()

    def exit_fullscreen(self):
        """Tam ekran modundan çıkar."""
        if self.is_fullscreen:
            root = self.winfo_toplevel()
            
            self.is_fullscreen = False
            root.attributes('-fullscreen', False)
            
            # Kontrol panelini göster
            self.control_panel.grid()
            
            # Kamera alanını düzelt
            self.camera_area.grid(column=1, columnspan=1)
            
            # Buton metnini güncelle
            self.fullscreen_button.config(text="🖥️ TAM EKRAN")
            
            logging.info("Normal ekran moduna dönüldü")

    def update_system_status(self, running):
        """Sistem durumunu günceller."""
        self.system_running = running
        
        if running:
            self.status_var.set("🟢 Sistem Aktif")
            self.control_var.set("SISTEMI DURDUR")
            self.control_button.config(bg=self.colors['accent_danger'])
        else:
            self.status_var.set("🔴 Sistem Kapalı")
            self.control_var.set("SISTEMI BAŞLAT")
            self.control_button.config(bg=self.colors['accent_primary'])

    def update_fall_detection(self, screenshot, confidence, event_data):
        """Düşme algılama sonucunu günceller."""
        # Ana thread'de güncelleme yap
        camera_id = event_data.get('camera_id', 'unknown')
        track_id = event_data.get('track_id', 'N/A')
        
        self.after(0, lambda: self._handle_fall_detection(camera_id, confidence, track_id))

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