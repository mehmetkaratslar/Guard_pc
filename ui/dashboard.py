# =======================================================================================
# DÜZELTME: Dashboard görüntü stabilitesi
# Sorunlar:
# 1. Çok sık frame update → Stabil güncelleme
# 2. Gereksiz image enhancement → Doğal görüntü kalitesi
# 3. Buffer yönetimi karmaşık → Basit ve stabil
# =======================================================================================


import tkinter as tk
from tkinter import ttk, messagebox
import logging
import cv2
from PIL import Image, ImageTk
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
    DÜZELTME: Stabil video display ile dashboard
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
        self.selected_camera_index = 0
        self.panel_collapsed = False  # Panel durumu
        
        # DÜZELTME: Stabil frame yönetimi
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.is_destroyed = False
        
        # DÜZELTME: Display optimizasyonu
        self.last_display_update = 0
        self.display_update_interval = 1.0 / 25  # 25 FPS display (stabil)
        
        # UI elementleri
        self.main_camera_label = None
        self.update_id = None
        
        # UI değişkenleri
        self.camera_info_var = tk.StringVar(value="Kamera seçilmedi")
        self.current_camera_var = tk.StringVar(value="Kamera seçilmedi")
        self.connection_status_var = tk.StringVar(value="🔴 Bağlantı Yok")
        self.fps_display_var = tk.StringVar(value="0 FPS")
        
        # DÜZELTME: Görsel düşme bildirimi için değişkenler
        self.fall_alert_var = tk.StringVar(value="")
        self.fall_alert_visible = False
        self.fall_alert_frame = None
        self.last_fall_alert_time = 0
        
        # Tracking istatistikleri
        self.tracking_stats = {
            'active_tracks': 0,
            'total_detections': 0,
            'fall_alerts': 0,
            'session_start': time.time(),
            'current_fps': 0
        }
        
        self.bind("<Destroy>", self._on_widget_destroy)

        # Modern tema - aynı
        self.colors = {
            'bg_primary': "#0D1117",
            'bg_secondary': "#161B22",
            'bg_tertiary': "#2A2F3A",
            'accent_primary': "#238636",
            'accent_danger': "#DA3633",
            'accent_warning': "#FB8500",
            'accent_info': "#1F6FEB",
            'text_primary': "#FFFFFF",
            'text_secondary': "#8B949E",
            'border': "#30363D",
            'hover': "#30363D"
        }

        # Tracking bilgileri değişkenleri
        self.tracking_info_vars = {
            'active_tracks': tk.StringVar(value="0"),
            'total_detections': tk.StringVar(value="0"),
            'fall_alerts': tk.StringVar(value="0"),
            'current_fps': tk.StringVar(value="0")
        }


        # Kontrol butonları değişkenleri
        self.control_var = tk.StringVar(value="SİSTEMİ BAŞLAT")
        self.status_var = tk.StringVar(value="🔴 Sistem Kapalı")

        # UI oluştur
        self._create_ultra_modern_ui()
        
        # Display update başlat
        self._start_stable_display_updates()

    def _create_ultra_modern_ui(self):
        """Ultra modern UI yapısını oluşturur - responsive ayarlar."""
        self.configure(bg=self.colors['bg_primary'])
        self.main_container = tk.Frame(self, bg=self.colors['bg_primary'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1, minsize=350)
        self.main_container.grid_columnconfigure(1, weight=5)
        self._create_control_panel()
        self._create_single_camera_area()
        
        # Panel toggle butonu - floating olarak ana container'da
        self.toggle_panel_btn = tk.Button(self.main_container, text="◀", 
                                         font=("Segoe UI", 12, "bold"),
                                         bg=self.colors['accent_primary'], 
                                         fg="white",
                                         command=self._toggle_panel,
                                         relief=tk.FLAT, 
                                         cursor="hand2", 
                                         padx=8, 
                                         pady=5,
                                         bd=0)
        # Başlangıçta sol üst köşeye yerleştir
    
        self.bind_all("<Left>", lambda e: self._previous_camera())
        self.bind_all("<Right>", lambda e: self._next_camera())
        # FIXED: Responsive font sistemi
        self._setup_configure_binding()

    def _setup_configure_binding(self):
        """Configure event binding'ini güvenli şekilde ayarla."""
        try:
            if self.winfo_exists():
                root = self.winfo_toplevel()
                if root.winfo_exists():
                    self._configure_binding_id = root.bind("<Configure>", self._safe_update_fonts)
        except:
            pass

    def _safe_update_fonts(self, event=None):
        """Güvenli font güncelleme."""
        try:
            if self.is_destroyed or not self.winfo_exists():
                return
            self._update_fonts()
        except:
            pass

    def _create_control_panel(self):
        """Sol kontrol panelini oluşturur."""
        self.control_panel = tk.Frame(self.main_container, bg=self.colors['bg_secondary'])
        self.control_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
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
    
        
        # Menü butonları
        self._create_menu_section(scrollable_frame)

    def _create_header_section(self, parent):
        """Header section - üst kısımda ortalanmış kullanıcı bilgisi."""
        header_frame = tk.Frame(parent, bg=self.colors['bg_tertiary'], height=120)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        # Ana header container - grid kullanarak tam ortalama
        header_grid = tk.Frame(header_frame, bg=self.colors['bg_tertiary'])
        header_grid.pack(fill=tk.BOTH, expand=True)
        header_grid.grid_columnconfigure(0, weight=1)  # Sol boşluk
        header_grid.grid_columnconfigure(1, weight=0)  # Orta - kullanıcı bilgisi
        header_grid.grid_columnconfigure(2, weight=1)  # Sağ boşluk
        header_grid.grid_rowconfigure(0, weight=1)
        
        # Sol taraf - Logo 
        left_frame = tk.Frame(header_grid, bg=self.colors['bg_tertiary'])
        left_frame.grid(row=0, column=0, sticky="w", padx=20)
        
        title_label = tk.Label(left_frame, text="🛡️ GUARD AI", 
                              font=("Segoe UI", self._responsive_font(18, 0.025)),
                              fg=self.colors['accent_primary'], bg=self.colors['bg_tertiary'])
        title_label.pack(anchor="w", pady=20)
        
        # Orta - Kullanıcı bilgisi (TAM ORTALANMIŞ)
        center_frame = tk.Frame(header_grid, bg=self.colors['bg_secondary'], relief=tk.RAISED, bd=2)
        center_frame.grid(row=0, column=1, sticky="", padx=20, pady=15)  # sticky="" = ortalanmış
        
        # Kullanıcı bilgi containerı
        user_info_frame = tk.Frame(center_frame, bg=self.colors['bg_secondary'])
        user_info_frame.pack(padx=25, pady=15)
        
        # Kullanıcı adı - ortalanmış
        user_name = self.user.get('displayName', self.user.get('email', 'Kullanıcı'))
        user_label = tk.Label(user_info_frame, text=f"👤 {user_name}", 
                             font=("Segoe UI", self._responsive_font(16, 0.02), "bold"),
                             fg=self.colors['text_primary'], bg=self.colors['bg_secondary'])
        user_label.pack(anchor="center", pady=(0, 3))
        
        # Email - ortalanmış
        user_email = self.user.get('email', '')
        if user_email:
            email_label = tk.Label(user_info_frame, text=user_email, 
                                 font=("Segoe UI", self._responsive_font(11, 0.015)),
                                 fg=self.colors['text_secondary'], bg=self.colors['bg_secondary'])
            email_label.pack(anchor="center")
            
        # Online durumu - ortalanmış
        status_label = tk.Label(user_info_frame, text="🟢 Çevrimiçi", 
                              font=("Segoe UI", self._responsive_font(10, 0.01)),
                              fg=self.colors['accent_primary'], bg=self.colors['bg_secondary'])
        status_label.pack(anchor="center", pady=(3, 0))
        
        # Sağ taraf - Boş (gelecekte ekstra bilgiler için)
        right_frame = tk.Frame(header_grid, bg=self.colors['bg_tertiary'])
        right_frame.grid(row=0, column=2, sticky="e", padx=20)

    def _responsive_font(self, base_size, rel=0.02):
        """Ekran boyutuna göre font büyüklüğü döndürür."""
        try:
            root = self.winfo_toplevel()
            w = root.winfo_width() or 1400
            h = root.winfo_height() or 900
            scale = min(w, h)
            return max(int(base_size * (scale / 900)), int(base_size * rel * (scale / 900)), 10)
        except:
            return base_size

    def _create_system_control_section(self, parent):
        """Sistem kontrolü section."""
        control_frame = tk.LabelFrame(parent, text="🔧 Sistem Kontrolü", 
                                     font=("Segoe UI", 14, "bold"),
                                     fg=self.colors['text_primary'], bg=self.colors['bg_secondary'],
                                     bd=1, relief="solid")
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Üst butonlar - Ayarlar ve Geçmiş
        top_buttons_frame = tk.Frame(control_frame, bg=self.colors['bg_secondary'])
        top_buttons_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        # Ayarlar butonu
        settings_btn = tk.Button(top_buttons_frame, text="⚙️ Ayarlar", 
                                font=("Segoe UI", 12, "bold"),
                                bg=self.colors['accent_info'], fg="white",
                                command=self.settings_fn,
                                relief=tk.FLAT, padx=15, pady=8, cursor="hand2")
        settings_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Olay geçmişi butonu
        history_btn = tk.Button(top_buttons_frame, text="📋 Olay Geçmişi", 
                               font=("Segoe UI", 12, "bold"),
                               bg=self.colors['accent_info'], fg="white",
                               command=self.history_fn,
                               relief=tk.FLAT, padx=15, pady=8, cursor="hand2")
        history_btn.pack(side=tk.LEFT, padx=5)
        
        # Ana kontrol butonu
        self.control_button = tk.Button(control_frame, textvariable=self.control_var,
                                       font=("Segoe UI", 16, "bold"),
                                       bg=self.colors['accent_primary'], fg="white",
                                       command=self._toggle_system,
                                       relief=tk.FLAT, pady=15, cursor="hand2",
                                       activebackground=self.colors['hover'])
        self.control_button.pack(fill=tk.X, padx=15, pady=10)
        
        # Sistem durumu
        status_label = tk.Label(control_frame, textvariable=self.status_var,
                               font=("Segoe UI", 14, "bold"), 
                               fg=self.colors['accent_danger'], bg=self.colors['bg_secondary'])
        status_label.pack(pady=(0, 15))
        

    def _create_camera_selector_section(self, parent):
        """Kamera seçici section."""
        camera_frame = tk.LabelFrame(parent, text="📹 Kamera Seçimi", 
                                    font=("Segoe UI", 14, "bold"),
                                    fg=self.colors['text_primary'], bg=self.colors['bg_secondary'],
                                    bd=1, relief="solid")
        camera_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Şu anki kamera bilgisi
        current_cam_frame = tk.Frame(camera_frame, bg=self.colors['bg_tertiary'])
        current_cam_frame.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(current_cam_frame, text="Aktif Kamera:", font=("Segoe UI", 12),
                fg=self.colors['text_secondary'], bg=self.colors['bg_tertiary']).pack(anchor="w")
        
        current_camera_label = tk.Label(current_cam_frame, textvariable=self.current_camera_var,
                                       font=("Segoe UI", 14, "bold"),
                                       fg=self.colors['accent_primary'], bg=self.colors['bg_tertiary'])
        current_camera_label.pack(anchor="w", pady=(5, 0))
        
        # Kamera listesi
        tk.Label(camera_frame, text="Kamera Listesi:", font=("Segoe UI", 12),
                fg=self.colors['text_secondary'], bg=self.colors['bg_secondary']).pack(anchor="w", padx=15, pady=(15, 5))
        
        # Kamera butonları
        self.camera_buttons = []
        for i, camera in enumerate(self.cameras):
            btn = tk.Button(camera_frame, text=f"📹 Kamera {camera.camera_index}",
                           font=("Segoe UI", 12), bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'],
                           command=lambda idx=i: self._select_camera(idx),
                           relief=tk.FLAT, pady=8, cursor="hand2",
                           activebackground=self.colors['hover'])
            btn.pack(fill=tk.X, padx=15, pady=2)
            self.camera_buttons.append(btn)
        
        # İlk kamerayı seç
        if self.cameras:
            self._select_camera(0)
        
        # Navigasyon butonları
        nav_frame = tk.Frame(camera_frame, bg=self.colors['bg_secondary'])
        nav_frame.pack(fill=tk.X, padx=15, pady=15)
        
        prev_btn = tk.Button(nav_frame, text="◀ Önceki", font=("Segoe UI", 10),
                            bg=self.colors['accent_info'], fg="white",
                            command=self._previous_camera, relief=tk.FLAT, cursor="hand2")
        prev_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        next_btn = tk.Button(nav_frame, text="Sonraki ▶", font=("Segoe UI", 10),
                            bg=self.colors['accent_info'], fg="white",
                            command=self._next_camera, relief=tk.FLAT, cursor="hand2")
        next_btn.pack(side=tk.RIGHT, padx=(5, 0))

    def _create_stats_section(self, parent):
        """Canlı istatistikler section."""
        stats_frame = tk.LabelFrame(parent, text="📊 Canlı İstatistikler", 
                                   font=("Segoe UI", 14, "bold"),
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
            
            tk.Label(left_frame, text=icon, font=("Segoe UI", 16),
                    bg=self.colors['bg_tertiary']).pack(side=tk.LEFT)
            tk.Label(left_frame, text=label, font=("Segoe UI", 12),
                    fg=self.colors['text_secondary'], bg=self.colors['bg_tertiary']).pack(side=tk.LEFT, padx=(5, 0))
            
            # Değer
            value_label = tk.Label(stat_card, textvariable=self.tracking_info_vars[key],
                                  font=("Segoe UI", 16, "bold"), fg=self.colors['accent_primary'],
                                  bg=self.colors['bg_tertiary'])
            value_label.pack(side=tk.RIGHT, pady=10, padx=10)



    def _create_menu_section(self, parent):
        """Alt kısım - Çıkış butonu."""
        # Spacer frame - boş alan
        spacer_frame = tk.Frame(parent, bg=self.colors['bg_secondary'])
        spacer_frame.pack(fill=tk.BOTH, expand=True)
        
        # Alt buton frame
        bottom_frame = tk.Frame(parent, bg=self.colors['bg_secondary'])
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Çıkış butonu - en altta
        logout_btn = tk.Button(bottom_frame, text="🚪 ÇIKIŞ YAP", 
                              font=("Segoe UI", 14, "bold"),
                              bg=self.colors['accent_danger'], fg="white", 
                              command=self.logout_fn,
                              relief=tk.FLAT, cursor="hand2", pady=12)
        logout_btn.pack(fill=tk.X)

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
                                    font=("Segoe UI", 16, "bold"),
                                    fg=self.colors['accent_primary'], bg=self.colors['bg_tertiary'])
        camera_info_label.pack(anchor="w")
        
        # Sağ taraf - durum bilgileri
        right_info = tk.Frame(self.camera_header, bg=self.colors['bg_tertiary'])
        right_info.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=10)
        
        # Bağlantı durumu
        connection_label = tk.Label(right_info, textvariable=self.connection_status_var,
                                   font=("Segoe UI", 12), fg=self.colors['accent_danger'],
                                   bg=self.colors['bg_tertiary'])
        connection_label.pack(side=tk.LEFT, padx=10)
        
        # FPS bilgisi
        fps_label = tk.Label(right_info, textvariable=self.fps_display_var,
                            font=("Segoe UI", 12, "bold"), fg=self.colors['accent_primary'],
                            bg=self.colors['bg_tertiary'])
        fps_label.pack(side=tk.LEFT, padx=10)
        
        # ANA KAMERA GÖRÜNTÜ ALANI
        self.main_camera_frame = tk.Frame(self.camera_area, bg="#000000", highlightthickness=2,
                                         highlightbackground=self.colors['border'])
        self.main_camera_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        # Kamera label'ı
        self.main_camera_label = tk.Label(self.main_camera_frame, bg="#000000", cursor="hand2")
        self.main_camera_label.pack(fill=tk.BOTH, expand=True)
        
        # İlk placeholder'ı göster
        self._show_camera_placeholder()
        
        # DÜZELTME: Görsel düşme bildirimi alanı oluştur
        self._create_fall_alert_overlay()

    def _show_camera_placeholder(self):
        """YOLOv11 optimize kamera placeholder'ını gösterir."""
        # YOLOv11 için 640x640 kare placeholder
        placeholder = np.zeros((640, 640, 3), dtype=np.uint8)
        
        for i in range(640):
            color_intensity = int(20 + (i / 640) * 30)
            placeholder[i, :] = [color_intensity, color_intensity, color_intensity]
        
        cv2.putText(placeholder, "GUARD", (200, 250), cv2.FONT_HERSHEY_SIMPLEX,
                   1.8, (56, 134, 54), 3, cv2.LINE_AA)
        
      
        cv2.putText(placeholder, "Sistemi baslatmak icin", (200, 420), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (139, 148, 158), 1, cv2.LINE_AA)
        cv2.putText(placeholder, "'SISTEMI BASLAT' butonuna tiklayin", (130, 450), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (139, 148, 158), 1, cv2.LINE_AA)
        

        
        cv2.rectangle(placeholder, (30, 30), (610, 610), (56, 134, 54), 3)
        
        self._update_main_camera_display(placeholder)
    
    def _create_fall_alert_overlay(self):
        """DÜZELTME: Görsel düşme bildirimi overlay'i oluşturur."""
        # Overlay ana kamera frame'inin üzerinde floating olacak
        self.fall_alert_frame = tk.Frame(self.main_camera_frame, 
                                        bg=self.colors['accent_danger'],
                                        relief=tk.RAISED, bd=3)
        # Başlangıçta gizli
        self.fall_alert_frame.place_forget()
        
        # İçerik
        alert_content = tk.Frame(self.fall_alert_frame, bg=self.colors['accent_danger'])
        alert_content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Ana başlık
        alert_title = tk.Label(alert_content, 
                              text="🚨 DÜŞME ALGILANDI!", 
                              font=("Segoe UI", 16, "bold"),
                              fg="white", bg=self.colors['accent_danger'])
        alert_title.pack(pady=(0, 5))
        
        # Detay bilgisi
        self.fall_detail_label = tk.Label(alert_content,
                                         textvariable=self.fall_alert_var,
                                         font=("Segoe UI", 12),
                                         fg="white", bg=self.colors['accent_danger'],
                                         wraplength=300, justify=tk.LEFT)
        self.fall_detail_label.pack(pady=5)
        
        # Butonlar
        button_frame = tk.Frame(alert_content, bg=self.colors['accent_danger'])
        button_frame.pack(pady=(10, 0))
        
        close_btn = tk.Button(button_frame, text="✅ TAMAM",
                             font=("Segoe UI", 10, "bold"),
                             bg="white", fg=self.colors['accent_danger'],
                             command=self._hide_fall_alert,
                             relief=tk.FLAT, padx=15, pady=5)
        close_btn.pack(side=tk.LEFT, padx=5)
        
        details_btn = tk.Button(button_frame, text="📋 DETAYLAR",
                               font=("Segoe UI", 10, "bold"),
                               bg="white", fg=self.colors['accent_danger'],
                               command=self.history_fn,
                               relief=tk.FLAT, padx=15, pady=5)
        details_btn.pack(side=tk.LEFT, padx=5)
    
    def _show_fall_alert(self, confidence, camera_id, timestamp):
        """DÜZELTME: Görsel düşme bildirimi gösterir."""
        try:
            current_time = time.time()
            
            # Çok sık bildirim önleme (5 saniye)
            if current_time - self.last_fall_alert_time < 5:
                return
                
            self.last_fall_alert_time = current_time
            
            # Bildirim metnini güncelle
            alert_text = f"""⏰ Zaman: {datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}
📹 Kamera: {camera_id}
🎯 Güven: {confidence*100:.1f}%
📊 Durum: {'Yüksek Risk' if confidence > 0.8 else 'Orta Risk'}"""
            
            self.fall_alert_var.set(alert_text)
            
            # Overlay'i göster - kamera görüntüsünün üst ortasında
            if self.main_camera_frame.winfo_exists():
                frame_width = self.main_camera_frame.winfo_width()
                frame_height = self.main_camera_frame.winfo_height()
                
                if frame_width > 100 and frame_height > 100:
                    alert_width = 400
                    alert_height = 180
                    
                    x = (frame_width - alert_width) // 2
                    y = 20  # Üstten 20px
                    
                    self.fall_alert_frame.place(x=x, y=y, width=alert_width, height=alert_height)
                    self.fall_alert_visible = True
                    
                    # 10 saniye sonra otomatik gizle
                    self.after(10000, self._auto_hide_fall_alert)
                    
                    logging.info("📢 Görsel düşme bildirimi gösterildi")
                    
        except Exception as e:
            logging.error(f"Fall alert gösterme hatası: {e}")
    
    def _hide_fall_alert(self):
        """DÜZELTME: Görsel düşme bildirimini gizler."""
        try:
            if self.fall_alert_frame:
                self.fall_alert_frame.place_forget()
                self.fall_alert_visible = False
                logging.info("📢 Görsel düşme bildirimi gizlendi")
        except Exception as e:
            logging.error(f"Fall alert gizleme hatası: {e}")
    
    def _auto_hide_fall_alert(self):
        """DÜZELTME: Otomatik gizleme."""
        if self.fall_alert_visible:
            self._hide_fall_alert()

    def _select_camera(self, camera_index):
        """Kamera seçer."""
        if 0 <= camera_index < len(self.cameras):
            self.selected_camera_index = camera_index
            camera = self.cameras[camera_index]
            
            self.current_camera_var.set(f"Kamera {camera.camera_index}")
            self.camera_info_var.set(f"📹 Kamera {camera.camera_index} - Doğal Kalite")
            
            for i, btn in enumerate(self.camera_buttons):
                if i == camera_index:
                    btn.config(bg=self.colors['accent_primary'], fg="white")
                else:
                    btn.config(bg=self.colors['bg_tertiary'], fg=self.colors['text_primary'])
            
            logging.info(f"Kamera {camera_index} seçildi - doğal ayarlar")

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

    def _start_stable_display_updates(self):
        """DÜZELTME: Stabil display güncelleme başlat."""
        self._stable_display_update()

    def _stable_display_update(self):
        """FIXED: Ultra stabil display update - tüm sorunlar çözülmüş."""
        if self.is_destroyed:
            return
        
        try:
            # Sistem başlatılmadıysa placeholder göster
            if not self.system_running:
                # Sadece 1 saniyede bir kontrol et
                self.update_id = self.after(1000, self._stable_display_update)
                return
            
            # Kamera seçili değilse veya çalışmıyorsa
            if (not self.cameras or 
                self.selected_camera_index >= len(self.cameras) or
                not self.cameras[self.selected_camera_index].is_running):
                # Sadece 500ms'de bir kontrol et
                self.update_id = self.after(500, self._stable_display_update)
                return
            
            # DÜZELTME: current_frame varsa onu göster (AI processing sonucu)
            with self.frame_lock:
                if self.current_frame is not None:
                    frame = self.current_frame.copy()
                    # Debug: AI frame kullanıldığını logla
                    if not hasattr(self, '_ai_frame_logged'):
                        logging.info("🎨 Dashboard: AI processed frame kullanılıyor")
                        self._ai_frame_logged = True
                else:
                    # Frame'i direkt kameradan al
                    camera = self.cameras[self.selected_camera_index]
                    frame = camera.get_frame()
                    # Reset AI frame log flag
                    if hasattr(self, '_ai_frame_logged'):
                        delattr(self, '_ai_frame_logged')
            
            if frame is not None and frame.size > 0:
                # Direkt display - AI processing sonucu dahil
                self._direct_stable_display(frame)
            
            # UI bilgilerini güncelle - 3 saniyede bir
            if int(time.time()) % 3 == 0:
                self._update_ui_info()
        
        except Exception as e:
            logging.error(f"Display update hatası: {e}")
        
        # FIXED: Sabit 25 FPS için 40ms
        self.update_id = self.after(40, self._stable_display_update)

    def _direct_stable_display(self, frame):
        """FIXED: Direkt ve ultra stabil display - minimum işlem."""
        try:
            # FIXED: Label boyutunu al
            label_width = self.main_camera_label.winfo_width() or 1200
            label_height = self.main_camera_label.winfo_height() or 800
            
            if label_width > 50 and label_height > 50:
                h, w = frame.shape[:2]
                
                # FIXED: Aspect ratio korunarak resize
                scale = min(label_width / w, label_height / h)
                new_width = int(w * scale)
                new_height = int(h * scale)
                
                # FIXED: Stabil resize - INTER_LINEAR daha hızlı
                resized = cv2.resize(frame, (new_width, new_height), 
                                interpolation=cv2.INTER_LINEAR)
                
                # FIXED: Minimal overlay
                self._add_minimal_overlay(resized)
                
                # FIXED: BGR to RGB
                frame_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                
                # FIXED: PIL ve PhotoImage
                from PIL import Image, ImageTk
                pil_image = Image.fromarray(frame_rgb)
                tk_image = ImageTk.PhotoImage(pil_image)
                
                # FIXED: GUI update
                self.main_camera_label.configure(image=tk_image)
                self.main_camera_label.image = tk_image
        
        except Exception as e:
            logging.error(f"Direct display hatası: {e}")

    def _add_minimal_overlay(self, frame):
        """FIXED: Ultra stabil mode göstergesi ile overlay."""
        try:
            h, w = frame.shape[:2]
            
            # FIXED: Timestamp
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            # FIXED: Şeffaf alan - daha büyük
            overlay = frame.copy()
            cv2.rectangle(overlay, (5, 5), (200, 45), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            # FIXED: Timestamp
            cv2.putText(frame, timestamp, (8, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 1, cv2.LINE_AA)
            
            # FIXED: Ultra stabil mode indicator
            cv2.putText(frame, "ULTRA STABIL", (8, 35), cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, (0, 255, 255), 1, cv2.LINE_AA)
            
            # FIXED: Kamera ID
            if self.selected_camera_index < len(self.cameras):
                camera = self.cameras[self.selected_camera_index]
                cam_text = f"CAM{camera.camera_index}"
                cv2.putText(frame, cam_text, (w-60, h-8), cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, (255, 255, 255), 1, cv2.LINE_AA)
        
        except Exception as e:
            logging.debug(f"Ultra overlay hatası: {e}")

    def _natural_display_update(self, frame):
        """
        DÜZELTME: Doğal görüntü kalitesi ile display update
        """
        try:
            # DÜZELTME: Label boyutlarını al
            display_width = self.main_camera_label.winfo_width() or 1200
            display_height = self.main_camera_label.winfo_height() or 800
            
            if display_width > 50 and display_height > 50:
                h, w = frame.shape[:2]
                
                # DÜZELTME: Aspect ratio korunarak resize
                aspect = w / h
                if display_width / display_height > aspect:
                    new_height = display_height
                    new_width = int(new_height * aspect)
                else:
                    new_width = display_width
                    new_height = int(new_width / aspect)
                
                # DÜZELTME: Yumuşak resize
                resized = cv2.resize(frame, (new_width, new_height), 
                                   interpolation=cv2.INTER_LINEAR)
                
                # DÜZELTME: Minimal overlay - doğal kalite
                self._add_natural_overlay(resized)
                
                # DÜZELTME: Doğal display
                self._direct_natural_display(resized)
        
        except Exception as e:
            logging.error(f"Natural display update hatası: {e}")

    def _add_natural_overlay(self, frame):
        """
        DÜZELTME: Çok minimal overlay - doğal kalite korunur
        """
        try:
            h, w = frame.shape[:2]
            
            # DÜZELTME: Sadece timestamp - minimal müdahale
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            # DÜZELTME: Şeffaf overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (150, 30), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            
            # DÜZELTME: Minimal text
            cv2.putText(frame, timestamp, (5, 20), cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, (0, 255, 136), 2, cv2.LINE_AA)
            
            # DÜZELTME: Kamera ID - köşede, küçük
            if self.selected_camera_index < len(self.cameras):
                camera = self.cameras[self.selected_camera_index]
                cam_text = f"CAM{camera.camera_index}"
                cv2.putText(frame, cam_text, (w-80, h-10), cv2.FONT_HERSHEY_SIMPLEX,
                           0.4, (255, 255, 255), 1, cv2.LINE_AA)
        
        except Exception as e:
            logging.debug(f"Natural overlay hatası: {e}")

    def _direct_natural_display(self, frame):
        """
        DÜZELTME: Doğal kalite display - enhancement yok
        """
        try:
            # DÜZELTME: Direct BGR to RGB - enhancement yok
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # DÜZELTME: PIL conversion - doğal kalite
            pil_image = Image.fromarray(frame_rgb)
            
            # DÜZELTME: Enhancement YOK - doğal kalite korunuyor
            # enhancer = ImageEnhance.Brightness(pil_image)
            # pil_image = enhancer.enhance(1.05)  # KALDIRILDI
            
            # DÜZELTME: PhotoImage
            tk_image = ImageTk.PhotoImage(pil_image)
            
            # DÜZELTME: Label güncelle
            self.main_camera_label.configure(image=tk_image)
            self.main_camera_label.image = tk_image
            
        except Exception as e:
            logging.error(f"Natural display hatası: {e}")

    def _update_main_camera_display(self, frame):
        """DÜZELTME: Ana kamera display - doğal kalite."""
        try:
            if len(frame.shape) == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame
            
            # DÜZELTME: PIL conversion - enhancement YOK
            pil_image = Image.fromarray(frame_rgb)
            
            # DÜZELTME: Enhancement KALDIRILDI - doğal kalite
            # enhancer = ImageEnhance.Brightness(pil_image)
            # pil_image = enhancer.enhance(1.05)
            # enhancer = ImageEnhance.Contrast(pil_image)
            # pil_image = enhancer.enhance(1.1)
            
            tk_image = ImageTk.PhotoImage(pil_image)
            
            self.main_camera_label.configure(image=tk_image)
            self.main_camera_label.image = tk_image
            
        except Exception as e:
            logging.error(f"Main camera display güncelleme hatası: {e}")

    def _update_ui_info(self):
        """UI bilgilerini günceller."""
        try:
            self.tracking_info_vars['active_tracks'].set(str(self.tracking_stats['active_tracks']))
            self.tracking_info_vars['total_detections'].set(str(self.tracking_stats['total_detections']))
            self.tracking_info_vars['fall_alerts'].set(str(self.tracking_stats['fall_alerts']))
            self.tracking_info_vars['current_fps'].set(str(self.tracking_stats['current_fps']))
            
            if self.selected_camera_index < len(self.cameras):
                camera = self.cameras[self.selected_camera_index]
                
                if self.system_running and camera.is_running:
                    self.connection_status_var.set("🟢 Bağlı")
                    self.fps_display_var.set(f"{self.tracking_stats['current_fps']} FPS")
                else:
                    self.connection_status_var.set("🔴 Bağlantı Yok")
                    self.fps_display_var.set("0 FPS")
            
        except Exception as e:
            logging.error(f"UI info güncelleme hatası: {e}")

    def _handle_fall_detection(self, camera_index, confidence, track_id):
        """DÜZELTME: Enhanced fall detection handler."""
        try:
            now = datetime.datetime.now()
            
            # Stats güncelle
            self.tracking_stats['fall_alerts'] += 1
            
            # UI güncelle
            self.event_time_var.set(f"🕐 {now.strftime('%H:%M:%S')}")
            self.event_conf_var.set(f"🎯 Güven: {confidence:.3f}")
            self.event_id_var.set(f"🔍 ID: {track_id}")
            
            # DÜZELTME: Enhanced logging
            logging.warning(f"🚨 ULTRA HASSAS DÜŞME ALGILANDI!")
            logging.info(f"   📍 Kamera: {camera_index}")
            logging.info(f"   🆔 Track ID: {track_id}")
            logging.info(f"   📊 Confidence: {confidence:.4f}")
            logging.info(f"   🕐 Zaman: {now.strftime('%H:%M:%S')}")
            
            # Sesli uyarı
            try:
                threading.Thread(target=lambda: winsound.PlaySound("SystemExclamation", 
                                                                winsound.SND_ALIAS), 
                            daemon=True).start()
            except:
                pass
            
            # Enhanced popup
            self._show_enhanced_fall_alert(confidence, track_id, now)
            
        except Exception as e:
            logging.error(f"Enhanced fall detection handler hatası: {e}")

    def _show_enhanced_fall_alert(self, confidence, track_id, timestamp):
        """DÜZELTME: Gelişmiş düşme uyarısı popup'ı."""
        try:
            alert_frame = tk.Toplevel(self)
            alert_frame.title("🚨 ULTRA HASSAS DÜŞME ALGILANDI!")
            alert_frame.geometry("500x300")
            alert_frame.configure(bg=self.colors['accent_danger'])
            alert_frame.transient(self.winfo_toplevel())
            alert_frame.grab_set()
            
            # Ana başlık
            tk.Label(alert_frame, text="🚨 DÜŞME ALGILANDI!", 
                    font=("Segoe UI", 20, "bold"), fg="white", 
                    bg=self.colors['accent_danger']).pack(pady=20)
            
            # Detay bilgiler
            info_frame = tk.Frame(alert_frame, bg=self.colors['accent_danger'])
            info_frame.pack(pady=10)
            
            details = [
                f"🎯 Güven Oranı: {confidence:.4f}",
                f"🆔 Track ID: {track_id}",
                f"🕐 Zaman: {timestamp.strftime('%H:%M:%S')}",
                f"📅 Tarih: {timestamp.strftime('%d/%m/%Y')}",
                f"🤖 Ultra Hassas Mod: AKTIF"
            ]
            
            for detail in details:
                tk.Label(info_frame, text=detail, 
                        font=("Segoe UI", 12), fg="white", 
                        bg=self.colors['accent_danger']).pack(pady=2)
            
            # Butonlar
            button_frame = tk.Frame(alert_frame, bg=self.colors['accent_danger'])
            button_frame.pack(pady=20)
            
            tk.Button(button_frame, text="✅ TAMAM", font=("Segoe UI", 14, "bold"),
                    bg="white", fg=self.colors['accent_danger'],
                    command=alert_frame.destroy, padx=20, pady=10).pack(side=tk.LEFT, padx=10)
            
            tk.Button(button_frame, text="📋 KAYDET", font=("Segoe UI", 14, "bold"),
                    bg="yellow", fg="black",
                    command=lambda: self._save_fall_log(confidence, track_id, timestamp),
                    padx=20, pady=10).pack(side=tk.LEFT, padx=10)
            
            # 7 saniye sonra otomatik kapat
            alert_frame.after(7000, alert_frame.destroy)
            
        except Exception as e:
            logging.error(f"Enhanced fall alert gösterme hatası: {e}")

    def _show_fall_alert_popup(self, confidence, camera_id, timestamp):
        """DÜZELTME: Düşme uyarısı popup'ı gösterir - ayrı metod."""
        try:
            alert_frame = tk.Toplevel(self)
            alert_frame.title("🚨 DÜŞME ALGILANDI!")
            alert_frame.geometry("450x250")
            alert_frame.configure(bg=self.colors['accent_danger'])
            alert_frame.transient(self.winfo_toplevel())
            alert_frame.grab_set()
            
            # Ana başlık
            tk.Label(alert_frame, text="🚨 DÜŞME ALGILANDI!", 
                    font=("Segoe UI", 16, "bold"), fg="white", bg=self.colors['accent_danger']).pack(pady=15)
            
            # Detaylar
            info_frame = tk.Frame(alert_frame, bg=self.colors['accent_danger'])
            info_frame.pack(pady=10, padx=20, fill='x')
            
            tk.Label(info_frame, text=f"📹 Kamera: {camera_id}", 
                    font=("Segoe UI", 11), fg="white", bg=self.colors['accent_danger']).pack(anchor='w')
            
            tk.Label(info_frame, text=f"📊 Güven Oranı: {confidence:.3f}", 
                    font=("Segoe UI", 11), fg="white", bg=self.colors['accent_danger']).pack(anchor='w', pady=2)
            
            timestamp_str = datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            tk.Label(info_frame, text=f"🕐 Zaman: {timestamp_str}", 
                    font=("Segoe UI", 11), fg="white", bg=self.colors['accent_danger']).pack(anchor='w', pady=2)
            
            # Butonlar
            btn_frame = tk.Frame(alert_frame, bg=self.colors['accent_danger'])
            btn_frame.pack(pady=15)
            
            tk.Button(btn_frame, text="TAMAM", font=("Segoe UI", 12, "bold"),
                     bg="white", fg=self.colors['accent_danger'], width=12,
                     command=alert_frame.destroy, pady=8).pack(side='left', padx=5)
            
            tk.Button(btn_frame, text="DETAYLAR", font=("Segoe UI", 12, "bold"),
                     bg=self.colors['bg_secondary'], fg="white", width=12,
                     command=lambda: (alert_frame.destroy(), self.history_fn()), pady=8).pack(side='left', padx=5)
            
            # 8 saniye sonra otomatik kapat
            alert_frame.after(8000, alert_frame.destroy)
            
            # Sesli uyarı
            try:
                import winsound
                winsound.Beep(1000, 500)
            except:
                pass
            
        except Exception as e:
            logging.error(f"Fall alert popup gösterme hatası: {e}")

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
            self.control_var.set("SİSTEMİ DURDUR")
            self.control_button.config(bg=self.colors['accent_danger'])
        else:
            self.status_var.set("🔴 Sistem Kapalı")
            self.control_var.set("SİSTEMİ BAŞLAT")
            self.control_button.config(bg=self.colors['accent_primary'])

    def update_fall_detection(self, screenshot, confidence, event_data):
        """DÜZELTME: Optimize edilmiş düşme algılama güncellemesi - sistem donmasını önler."""
        try:
            camera_id = event_data.get('camera_id', 'unknown')
            track_id = event_data.get('track_id', 'N/A')
            timestamp = event_data.get('timestamp', time.time())
            event_id = event_data.get('event_id', 'unknown')
            
            # DÜZELTME: Hızlı UI update - asenkron popup
            def quick_fall_notification():
                try:
                    # 1. Anında tracking stats güncelle
                    if hasattr(self, 'tracking_stats'):
                        self.tracking_stats['fall_alerts'] += 1
                    
                    # 2. Hızlı fall alert göster
                    self._show_quick_fall_alert(confidence, camera_id, timestamp, event_id)
                    
                    # 3. Background'da popup göster
                    self.after(200, lambda: self._show_delayed_popup(confidence, camera_id, timestamp, event_id))
                    
                    logging.info(f"✅ Quick dashboard notification: {event_id}")
                    
                except Exception as e:
                    logging.error(f"❌ Quick notification error: {e}")
            
            # DÜZELTME: Hemen UI thread'inde çalıştır
            self.after(0, quick_fall_notification)
            
        except Exception as e:
            logging.error(f"❌ Dashboard update error: {e}")

    def _show_quick_fall_alert(self, confidence, camera_id, timestamp, event_id):
        """DÜZELTME: Hızlı fall alert - minimum CPU kullanımı."""
        try:
            # Fall alert overlay hızlı göster
            if hasattr(self, 'fall_alert_frame') and self.fall_alert_frame:
                self.fall_alert_frame.destroy()
            
            # Basit overlay
            self.fall_alert_frame = tk.Frame(self, bg='red', relief=tk.RAISED, bd=5)
            self.fall_alert_frame.place(relx=0.5, rely=0.1, anchor='center')
            
            alert_text = f"🚨 DÜŞME ALGILANDI!\nGüven: {confidence:.2f}\nKamera: {camera_id}\nID: {event_id[:8]}"
            
            alert_label = tk.Label(self.fall_alert_frame, text=alert_text,
                                 font=("Segoe UI", 14, "bold"),
                                 fg='white', bg='red', padx=20, pady=15)
            alert_label.pack()
            
            # 3 saniye sonra otomatik gizle
            self.after(3000, self._hide_quick_alert)
            
        except Exception as e:
            logging.error(f"❌ Quick alert error: {e}")

    def _hide_quick_alert(self):
        """DÜZELTME: Hızlı alert gizleme."""
        try:
            if hasattr(self, 'fall_alert_frame') and self.fall_alert_frame:
                self.fall_alert_frame.destroy()
                self.fall_alert_frame = None
        except:
            pass

    def _show_delayed_popup(self, confidence, camera_id, timestamp, event_id):
        """DÜZELTME: Gecikmeli popup - background'da çalışır."""
        try:
            # Basit popup - sistem dondurmaz
            popup = tk.Toplevel(self)
            popup.title("Düşme Algılandı")
            popup.geometry("400x200")
            popup.configure(bg=self.colors['bg_primary'])
            popup.transient(self)
            popup.grab_set()
            
            # İçerik
            tk.Label(popup, text="🚨 DÜŞME ALGILANDI!", 
                    font=("Segoe UI", 16, "bold"),
                    fg=self.colors['accent_danger'], 
                    bg=self.colors['bg_primary']).pack(pady=20)
            
            info_text = f"Güven Oranı: {confidence:.2f}\nKamera: {camera_id}\nZaman: {time.strftime('%H:%M:%S', time.localtime(timestamp))}"
            
            tk.Label(popup, text=info_text,
                    font=("Segoe UI", 12),
                    fg=self.colors['text_primary'],
                    bg=self.colors['bg_primary']).pack(pady=10)
            
            # Kapat butonu
            tk.Button(popup, text="TAMAM", 
                     command=popup.destroy,
                     font=("Segoe UI", 12, "bold"),
                     bg=self.colors['accent_primary'], 
                     fg="white").pack(pady=20)
            
            # 5 saniye sonra otomatik kapat
            self.after(5000, lambda: popup.destroy() if popup.winfo_exists() else None)
            
        except Exception as e:
            logging.error(f"❌ Delayed popup error: {e}")

    def update_ai_frame(self, frame):
        """AI processing sonucu frame'i günceller."""
        try:
            with self.frame_lock:
                self.current_frame = frame
                # Debug log
                if hasattr(self, '_last_ai_update'):
                    if time.time() - self._last_ai_update > 1.0:
                        logging.debug(f"AI frame güncellendi - shape: {frame.shape if frame is not None else 'None'}")
                        self._last_ai_update = time.time()
                else:
                    self._last_ai_update = time.time()
        except Exception as e:
            logging.error(f"AI frame güncelleme hatası: {e}")

    def _on_widget_destroy(self, event):
        """Widget yok edildiğinde."""
        if event.widget == self:
            self.is_destroyed = True
            self._cleanup_resources()

    def _cleanup_resources(self):
        """DÜZELTME: Stabil kaynak temizleme."""
        try:
            self.is_destroyed = True
            
            # Configure binding'i temizle
            if hasattr(self, '_configure_binding_id') and self._configure_binding_id:
                try:
                    root = self.winfo_toplevel()
                    if root.winfo_exists():
                        root.unbind("<Configure>", self._configure_binding_id)
                except:
                    pass
            
            if hasattr(self, 'update_id') and self.update_id:
                self.after_cancel(self.update_id)
                self.update_id = None
            
            # Processing thread temizle
            if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=1.0)
            
            logging.info("Dashboard kaynakları güvenli şekilde temizlendi")
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

    def _update_fonts(self):
        """Tüm önemli widget'larda fontları güncelle."""
        try:
            if self.is_destroyed or not self.winfo_exists():
                return
            for widget in self.winfo_children():
                self._update_widget_font(widget)
        except:
            pass

    def _update_widget_font(self, widget):
        try:
            if not widget.winfo_exists():
                return
            if hasattr(widget, 'config') and 'font' in widget.keys():
                font = widget.cget('font')
                if isinstance(font, tuple):
                    base = font[1] if len(font) > 1 else 12
                    widget.config(font=(font[0], self._responsive_font(base)))
            for child in widget.winfo_children():
                self._update_widget_font(child)
        except:
            pass

    def _toggle_panel(self):
        """Sol paneli genişletir/daraltır."""
        if self.panel_collapsed:
            # Paneli genişlet
            self.control_panel.grid()
            self.main_container.grid_columnconfigure(0, weight=1, minsize=350)
            self.toggle_panel_btn.config(text="◀")
            self.toggle_panel_btn.place(x=360, y=10, anchor="nw")
            self.panel_collapsed = False
        else:
            # Paneli daralt
            self.control_panel.grid_remove()
            self.main_container.grid_columnconfigure(0, weight=0, minsize=0)
            self.toggle_panel_btn.config(text="▶")
            self.toggle_panel_btn.place(x=10, y=10, anchor="nw")
            self.panel_collapsed = True

