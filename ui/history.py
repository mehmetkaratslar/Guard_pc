# 🎨 ENHANCED HISTORY UI - Ultra Modern & Feature Rich (Hata Düzeltmesi)
# 📄 Dosya Adı: history.py
# 📁 Konum: guard_pc_app/ui/history.py
# 🎯 Açıklama: Guard sisteminin geçmiş olaylar ekranı için modern ve kullanıcı dostu bir arayüz.  
# ✨ Değişiklikler:
# - 🛠️ Hata Düzeltmesi: `glass` renk tanımı `rgba` yerine hex formatına çevrildi (Tkinter uyumluluğu için).
# - 🌈 Glassmorphism efekti, opak hex renklerle simüle edildi.
# - 📏 Mevcut düzen ve tasarım korundu, yalnızca renk tanımları güncellendi.
# 🔗 Bağımlılıklar:
# - Firebase (auth, firestore, storage)
# - Python kütüphaneleri: tkinter, PIL, requests, matplotlib, numpy
# - guard_pc_app/db_manager.py (veritabanı işlemleri için)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import datetime
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageDraw
import requests
from io import BytesIO
import threading
import time
import sys
import os
import json
import math
import colorsys
import firebase_admin
from firebase_admin import auth
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class HistoryFrame(ttk.Frame):
    """🚀 Ultra Modern & Premium Geçmiş Olaylar Ekranı"""

    def __init__(self, parent, user, db_manager, back_fn):
        # Ana frame'i başlat
        super().__init__(parent, style="MainFrame.TFrame")
        
        # Sınıf değişkenlerini tanımla
        self.user = user
        self.db_manager = db_manager
        self.back_fn = back_fn
        self.events = []
        self.filtered_events = []
        self.image_cache = {}
        self.current_image = None
        self.animation_speed = 200
        self.glassmorphism_enabled = True
        
        # 🎨 Tema sistemi (glass renkleri hex formatına çevrildi)
        self.themes = {
            "midnight": {
                "name": "Gece Mavisi",
                "primary": "#121212",
                "secondary": "#1E1E2E",
                "accent": "#40C4FF",
                "success": "#4CAF50",
                "warning": "#FFB300",
                "danger": "#F44336",
                "text": "#E0E0E0",
                "text_secondary": "#B0BEC5",
                "glass": "#2A2A3E"  # rgba(30,30,46,0.15) yerine opak hex
            },
            "ocean": {
                "name": "Okyanus Esintisi",
                "primary": "#0A192F",
                "secondary": "#263238",
                "accent": "#29B6F6",
                "success": "#26A69A",
                "warning": "#FFCA28",
                "danger": "#EF5350",
                "text": "#E1F5FE",
                "text_secondary": "#90CAF9",
                "glass": "#364B5A"  # rgba(41,182,246,0.15) yerine opak hex
            },
            "sunset": {
                "name": "Gün Batımı",
                "primary": "#311B92",
                "secondary": "#F06292",
                "accent": "#FF8A65",
                "success": "#4FC3F7",
                "warning": "#FFCA28",
                "danger": "#E91E63",
                "text": "#FCE4EC",
                "text_secondary": "#FFCCBC",
                "glass": "#F28A9F"  # rgba(255,138,101,0.15) yerine opak hex
            },
            "forest": {
                "name": "Orman Nefesi",
                "primary": "#1A3C34",
                "secondary": "#2E7D32",
                "accent": "#A5D6A7",
                "success": "#4CAF50",
                "warning": "#FFCA28",
                "danger": "#D32F2F",
                "text": "#E8F5E9",
                "text_secondary": "#C8E6C9",
                "glass": "#4A704C"  # rgba(165,214,167,0.15) yerine opak hex
            }
        }
        
        self.current_theme = "midnight"
        self.dark_mode = True
        
        # 🔍 Arama ve filtreleme
        self.search_history = []
        self.current_search = ""
        self.sort_order = "newest"
        self.view_mode = "cards"
        
        # 📊 İstatistikler
        self.stats = {
            "total_events": 0,
            "high_confidence": 0,
            "today_events": 0,
            "this_week": 0,
            "avg_confidence": 0.0
        }
        
        # 🎬 Animasyon
        self.animation_queue = []
        self.fade_widgets = []
        
        # 📸 Görüntü viewer
        self.zoom_level = 1.0
        self.rotation_angle = 0
        self.image_filters = {
            "none": "Orijinal",
            "enhance": "Geliştirilmiş",
            "night_vision": "Gece Görüş",
            "thermal": "Termal",
            "edge_detect": "Kenar Algılama"
        }
        self.current_filter = "none"
        
        # Tema, UI ve animasyonları kur
        self._setup_theme()
        self._create_modern_ui()
        self._setup_animations()
        self._load_events_with_stats()
        
        # 🎯 Olayları bağla
        self.bind("<Configure>", self._on_configure)
        self.bind("<Destroy>", self._on_destroy)

    def _setup_theme(self):
        """🎨 Tema renklerini ve stilleri ayarlar"""
        theme = self.themes[self.current_theme]
        
        self.colors = {
            'primary': theme["primary"],
            'secondary': theme["secondary"],
            'accent': theme["accent"],
            'success': theme["success"],
            'warning': theme["warning"],
            'danger': theme["danger"],
            'text': theme["text"],
            'text_secondary': theme["text_secondary"],
            'glass': theme["glass"]
        }
        
        # TTK stilleri
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Glass.TFrame", 
                       background=self.colors['secondary'],
                       relief="flat",
                       borderwidth=0)
        
        style.configure("MainFrame.TFrame", background=self.colors['primary'])
        style.configure("Header.TFrame", background=self.colors['primary'])
        style.configure("Card.TFrame", background=self.colors['secondary'])
        
        style.configure("Title.TLabel",
                       background=self.colors['primary'],
                       foreground=self.colors['text'],
                       font=("Segoe UI", 20, "bold"))
        
        style.configure("Subtitle.TLabel",
                       background=self.colors['secondary'],
                       foreground=self.colors['text_secondary'],
                       font=("Segoe UI", 11))
        
        style.configure("Accent.TButton",
                       background=self.colors['accent'],
                       foreground=self.colors['text'],
                       font=("Segoe UI", 10, "bold"),
                       relief="flat")

    def _create_modern_ui(self):
        """🎨 Modern ve şık UI oluşturur"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Header
        self.rowconfigure(1, weight=0)  # Stats Dashboard
        self.rowconfigure(2, weight=0)  # Controls
        self.rowconfigure(3, weight=1)  # Main Content
        
        self._create_animated_header()
        self._create_stats_dashboard()
        self._create_control_panel()
        self._create_main_content()

    def _create_animated_header(self):
        """🎨 Animasyonlu header oluşturur"""
        header_frame = ttk.Frame(self, style="Header.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        header_canvas = tk.Canvas(header_frame, height=70, highlightthickness=0)
        header_canvas.pack(fill=tk.BOTH, expand=True)
        
        self._create_gradient_background(header_canvas, self.colors['primary'], self.colors['accent'])
        
        header_content = ttk.Frame(header_canvas, style="Header.TFrame")
        header_canvas.create_window(0, 0, window=header_content, anchor="nw")
        
        back_frame = ttk.Frame(header_content, style="Header.TFrame")
        back_frame.pack(side=tk.LEFT, padx=15, pady=15)
        
        back_btn = tk.Button(back_frame,
                            text="⬅ Geri",
                            font=("Segoe UI", 11, "bold"),
                            bg=self.colors['accent'],
                            fg=self.colors['text'],
                            relief=tk.FLAT,
                            padx=15, pady=8,
                            cursor="hand2",
                            command=self._animated_back)
        back_btn.pack()
        
        back_btn.bind("<Enter>", lambda e: self._button_hover_effect(back_btn, True))
        back_btn.bind("<Leave>", lambda e: self._button_hover_effect(back_btn, False))
        
        title_frame = ttk.Frame(header_content, style="Header.TFrame")
        title_frame.pack(side=tk.LEFT, padx=15, pady=15)
        
        title_canvas = tk.Canvas(title_frame, width=250, height=35, highlightthickness=0,
                               bg=self.colors['primary'])
        title_canvas.pack()
        
        self._create_gradient_text(title_canvas, "📋 Olay Geçmişi", 
                                 self.colors['text'], self.colors['accent'])
        
        theme_frame = ttk.Frame(header_content, style="Header.TFrame")
        theme_frame.pack(side=tk.RIGHT, padx=15, pady=15)
        
        tk.Label(theme_frame, text="🎨", font=("Segoe UI", 14),
                bg=self.colors['primary'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.theme_var = tk.StringVar(value=self.themes[self.current_theme]["name"])
        theme_menu = ttk.OptionMenu(theme_frame, self.theme_var,
                                   self.themes[self.current_theme]["name"],
                                   *[theme["name"] for theme in self.themes.values()],
                                   command=self._change_theme)
        theme_menu.pack(side=tk.LEFT, padx=8)

    def _create_stats_dashboard(self):
        """📊 İstatistik dashboard'u oluşturur"""
        stats_frame = ttk.Frame(self, style="Glass.TFrame")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=10)
        
        stats_canvas = tk.Canvas(stats_frame, height=100, highlightthickness=0,
                               bg=self.colors['secondary'])
        stats_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.stats_cards = []
        card_width = 160
        card_height = 80
        
        stats_data = [
            ("📈", "Toplam Olay", "total_events", self.colors['accent']),
            ("⚠️", "Yüksek Risk", "high_confidence", self.colors['danger']),
            ("📅", "Bugün", "today_events", self.colors['warning']),
            ("📊", "Ort. Güven", "avg_confidence", self.colors['success'])
        ]
        
        for i, (icon, title, key, color) in enumerate(stats_data):
            x = i * (card_width + 15) + 15
            card = self._create_stat_card(stats_canvas, x, 10, card_width, card_height,
                                        icon, title, str(self.stats.get(key, 0)), color)
            self.stats_cards.append(card)

    def _create_stat_card(self, canvas, x, y, w, h, icon, title, value, color):
        """📊 İstatistik kartı oluşturur"""
        # Glassmorphism efekti için hex renk kullan
        card_bg = canvas.create_rectangle(x, y, x+w, y+h,
                                        fill=self.colors['glass'],  # Hex formatında renk
                                        outline=color,
                                        width=1)
        
        canvas.create_text(x+15, y+20, text=icon, font=("Segoe UI", 16),
                         fill=color, anchor="w")
        
        canvas.create_text(x+50, y+20, text=title, font=("Segoe UI", 9, "bold"),
                         fill=self.colors['text_secondary'], anchor="w")
        
        value_text = canvas.create_text(x+50, y+40, text=value, 
                                      font=("Segoe UI", 14, "bold"),
                                      fill=self.colors['text'], anchor="w")
        
        trend = "↗️" if hash(title) % 2 else "↘️"
        canvas.create_text(x+w-15, y+h-15, text=trend, font=("Segoe UI", 10),
                         fill=self.colors['success'] if trend == "↗️" else self.colors['warning'],
                         anchor="center")
        
        return {"bg": card_bg, "value": value_text}

    def _create_control_panel(self):
        """🔧 Gelişmiş kontrol paneli oluşturur"""
        control_frame = ttk.Frame(self, style="Glass.TFrame")
        control_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=10)
        
        inner_control = ttk.Frame(control_frame, style="Glass.TFrame")
        inner_control.pack(fill=tk.X, padx=10, pady=10)
        
        search_frame = ttk.Frame(inner_control, style="Glass.TFrame")
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(search_frame, text="🔍", font=("Segoe UI", 12),
                bg=self.colors['secondary'], fg=self.colors['accent']).pack(side=tk.LEFT, padx=5)
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                              font=("Segoe UI", 10),
                              bg=self.colors['secondary'],
                              fg=self.colors['text'],
                              insertbackground=self.colors['accent'],
                              relief=tk.FLAT,
                              width=25)
        search_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        search_entry.bind('<KeyRelease>', self._on_search_change)
        search_entry.bind('<Return>', self._advanced_search)
        
        date_frame = ttk.Frame(inner_control, style="Glass.TFrame")
        date_frame.pack(side=tk.LEFT, padx=15)
        
        tk.Label(date_frame, text="📅", font=("Segoe UI", 12),
                bg=self.colors['secondary'], fg=self.colors['accent']).pack(side=tk.LEFT)
        
        self.date_filter_var = tk.StringVar(value="Tüm Zamanlar")
        date_options = ["Bugün", "Bu Hafta", "Bu Ay", "Son 3 Ay", "Tüm Zamanlar", "Özel Aralık"]
        date_menu = ttk.OptionMenu(date_frame, self.date_filter_var, "Tüm Zamanlar",
                                 *date_options, command=self._apply_date_filter)
        date_menu.pack(side=tk.LEFT, padx=5)
        
        conf_frame = ttk.Frame(inner_control, style="Glass.TFrame")
        conf_frame.pack(side=tk.LEFT, padx=15)
        
        tk.Label(conf_frame, text="🎯", font=("Segoe UI", 12),
                bg=self.colors['secondary'], fg=self.colors['accent']).pack(side=tk.LEFT)
        
        self.conf_scale = tk.Scale(conf_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                 bg=self.colors['secondary'], fg=self.colors['text'],
                                 highlightthickness=0, length=100,
                                 command=self._apply_confidence_filter)
        self.conf_scale.pack(side=tk.LEFT, padx=5)
        
        view_frame = ttk.Frame(inner_control, style="Glass.TFrame")
        view_frame.pack(side=tk.RIGHT, padx=10)
        
        view_modes = [("🎴", "cards"), ("📋", "list"), ("⏱️", "timeline")]
        for icon, mode in view_modes:
            btn = tk.Button(view_frame, text=icon, font=("Segoe UI", 12),
                          bg=self.colors['accent'] if mode == self.view_mode else self.colors['secondary'],
                          fg=self.colors['text'],
                          relief=tk.FLAT, width=3,
                          command=lambda m=mode: self._change_view_mode(m))
            btn.pack(side=tk.LEFT, padx=2)
            
            btn.bind("<Enter>", lambda e, b=btn: self._button_hover_effect(b, True))
            btn.bind("<Leave>", lambda e, b=btn: self._button_hover_effect(b, False))

    def _create_main_content(self):
        """📋 Ana içerik alanını oluşturur"""
        main_frame = ttk.Frame(self, style="Glass.TFrame")
        main_frame.grid(row=3, column=0, sticky="nsew", padx=15, pady=10)
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(0, weight=1)
        
        self.events_container = ttk.Frame(main_frame, style="Glass.TFrame")
        self.events_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self._create_enhanced_image_viewer(main_frame)
        self._create_analytics_panel(main_frame)

    def _create_enhanced_image_viewer(self, parent):
        """🖼️ Gelişmiş görüntü görüntüleyici oluşturur"""
        viewer_frame = ttk.Frame(parent, style="Glass.TFrame")
        viewer_frame.grid(row=0, column=1, sticky="nsew")
        viewer_frame.columnconfigure(0, weight=1)
        viewer_frame.rowconfigure(0, weight=0)
        viewer_frame.rowconfigure(1, weight=1)
        viewer_frame.rowconfigure(2, weight=0)
        
        controls_frame = ttk.Frame(viewer_frame, style="Glass.TFrame")
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.image_info_var = tk.StringVar(value="Görüntü seçilmedi")
        tk.Label(controls_frame, textvariable=self.image_info_var,
                font=("Segoe UI", 10, "bold"),
                bg=self.colors['secondary'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        controls_right = ttk.Frame(controls_frame, style="Glass.TFrame")
        controls_right.pack(side=tk.RIGHT)
        
        control_buttons = [
            ("🔍+", self._zoom_in),
            ("🔍-", self._zoom_out),
            ("↻", self._rotate_image),
            ("🎨", self._apply_filter),
            ("💾", self._save_image),
            ("📤", self._export_image)
        ]
        
        for icon, command in control_buttons:
            btn = tk.Button(controls_right, text=icon, font=("Segoe UI", 10),
                          bg=self.colors['secondary'], fg=self.colors['accent'],
                          relief=tk.FLAT, width=3, height=1,
                          command=command)
            btn.pack(side=tk.LEFT, padx=2)
            
            btn.bind("<Enter>", lambda e, b=btn: self._button_hover_effect(b, True))
            btn.bind("<Leave>", lambda e, b=btn: self._button_hover_effect(b, False))
        
        image_frame = ttk.Frame(viewer_frame, style="Glass.TFrame")
        image_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self.image_canvas = tk.Canvas(image_frame,
                                    bg=self.colors['primary'],
                                    highlightthickness=1,
                                    highlightbackground=self.colors['accent'])
        self.image_canvas.pack(fill=tk.BOTH, expand=True)
        
        v_scrollbar = ttk.Scrollbar(image_frame, orient=tk.VERTICAL, command=self.image_canvas.yview)
        h_scrollbar = ttk.Scrollbar(image_frame, orient=tk.HORIZONTAL, command=self.image_canvas.xview)
        self.image_canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.image_canvas.bind("<Button-1>", self._start_pan)
        self.image_canvas.bind("<B1-Motion>", self._pan_image)
        self.image_canvas.bind("<MouseWheel>", self._mouse_zoom)
        self.image_canvas.bind("<Double-Button-1>", self._reset_image_view)
        
        analytics_frame = ttk.Frame(viewer_frame, style="Glass.TFrame")
        analytics_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        self.metadata_text = tk.Text(analytics_frame, height=4, font=("Consolas", 8),
                                   bg=self.colors['secondary'], fg=self.colors['text_secondary'],
                                   relief=tk.FLAT, wrap=tk.WORD)
        self.metadata_text.pack(fill=tk.X, padx=5, pady=5)

    def _start_pan(self, event):
        """🖱️ Pan başlatılırken fare pozisyonunu kaydet"""
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._canvas_start_scroll_x = self.image_canvas.xview()[0]
        self._canvas_start_scroll_y = self.image_canvas.yview()[0]

    def _pan_image(self, event):
        """🖱️ Pan sırasında resmi hareket ettir"""
        dx = event.x - self._pan_start_x
        dy = event.y - self._pan_start_y
        self.image_canvas.xview_moveto(self._canvas_start_scroll_x - dx / self.image_canvas.winfo_width())
        self.image_canvas.yview_moveto(self._canvas_start_scroll_y - dy / self.image_canvas.winfo_height())

    def _mouse_zoom(self, event):
        """🖱️ Fare tekerleği ile zoom yap"""
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    def _create_analytics_panel(self, parent):
        """📊 Analitik paneli oluşturur"""
        pass

    def _setup_animations(self):
        """🎬 Animasyon sistemini kurar"""
        self.animation_running = False
        self.fade_step = 0.0

    def _create_gradient_background(self, canvas, color1, color2):
        """🌈 Gradient arka plan oluşturur"""
        canvas.delete("gradient")
        width = canvas.winfo_reqwidth() or 800
        height = canvas.winfo_reqheight() or 70
        
        r1, g1, b1 = self._hex_to_rgb(color1)
        r2, g2, b2 = self._hex_to_rgb(color2)
        
        for i in range(height):
            ratio = i / height
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            canvas.create_line(0, i, width, i, fill=color, tags="gradient")

    def _create_gradient_text(self, canvas, text, color1, color2):
        """✨ Gradient metin efekti oluşturur"""
        canvas.create_text(10, 18, text=text, font=("Segoe UI", 16, "bold"),
                         fill=color1, anchor="w")
        canvas.create_text(12, 20, text=text, font=("Segoe UI", 16, "bold"),
                         fill=color2, anchor="w")

    def _button_hover_effect(self, button, entering):
        """✨ Buton hover efekti"""
        if entering:
            original_bg = button.cget('bg')
            button._original_bg = original_bg
            button.configure(bg=self._lighten_color(original_bg, 0.15))
            self._animate_button_scale(button, 1.03)
        else:
            if hasattr(button, '_original_bg'):
                button.configure(bg=button._original_bg)
            else:
                button.configure(bg=self.colors['secondary'])
            self._animate_button_scale(button, 1.0)

    def _animate_button_scale(self, button, target_scale):
        """🎬 Buton ölçek animasyonu"""
        # Butonun mevcut fontunu al
        current_font = button.cget('font')
        # Font string ise ayrıştır
        if isinstance(current_font, str):
            font_parts = current_font.split()
            try:
                # Font boyutunu al (ikinci eleman genellikle boyut olur)
                size = int(font_parts[1])
                # Yeni boyutu hesapla
                new_size = int(size * target_scale)
                # Yeni fontu oluştur (kalan özellikler korunur)
                button.configure(font=(font_parts[0], new_size) + tuple(font_parts[2:]))
            except (IndexError, ValueError):
                # Font formatı beklenmedikse varsayılan boyuta dön
                default_size = 11
                new_size = int(default_size * target_scale)
                button.configure(font=(font_parts[0] if font_parts else "Segoe UI", new_size))
        else:
            # Font string değilse varsayılan font ve boyut kullan
            default_size = 11
            new_size = int(default_size * target_scale)
            button.configure(font=("Segoe UI", new_size))



    def _hex_to_rgb(self, hex_color):
        """🎨 Hex rengi RGB'ye çevirir"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _lighten_color(self, hex_color, factor):
        """🌟 Rengi açar"""
        r, g, b = self._hex_to_rgb(hex_color)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _animated_back(self):
        """🎬 Animasyonlu geri dönüş"""
        self._fade_out_widgets()
        self.after(200, self.back_fn)

    def _fade_out_widgets(self):
        """🎬 Widget'ları fade out yapar"""
        for child in self.winfo_children():
            self._animate_widget_fade(child, 1.0, 0.0)

    def _animate_widget_fade(self, widget, start_alpha, end_alpha):
        """🎬 Widget fade animasyonu"""
        steps = 8
        for i in range(steps):
            alpha = start_alpha + (end_alpha - start_alpha) * (i / steps)
            self.after(i * 25, lambda a=alpha, w=widget: self._apply_alpha_to_widget(w, a))

    def _apply_alpha_to_widget(self, widget, alpha):
        """🎨 Widget'a alpha efekti uygular"""
        try:
            if hasattr(widget, 'configure'):
                current_bg = widget.cget('background') if 'background' in widget.configure() else None
                if current_bg:
                    r, g, b = self._hex_to_rgb(current_bg)
                    r = int(r * alpha)
                    g = int(g * alpha)
                    b = int(b * alpha)
                    new_color = f"#{r:02x}{g:02x}{b:02x}"
                    widget.configure(background=new_color)
        except:
            pass

    def _change_theme(self, theme_name):
        """🎨 Tema değiştirme"""
        for theme_key, theme_data in self.themes.items():
            if theme_data["name"] == theme_name:
                self.current_theme = theme_key
                break
        
        self._setup_theme()
        self._refresh_ui()

    def _refresh_ui(self):
        """🔄 UI'yı yenile"""
        for child in self.winfo_children():
            child.destroy()
        self._create_modern_ui()

    def _change_view_mode(self, mode):
        """👁️ Görünüm modunu değiştir"""
        self.view_mode = mode
        self._update_events_display()

    def _update_events_display(self):
        """📋 Olayları görünüm moduna göre güncelle"""
        for child in self.events_container.winfo_children():
            child.destroy()
        
        if self.view_mode == "cards":
            self._create_card_view()
        elif self.view_mode == "list":
            self._create_list_view()
        elif self.view_mode == "timeline":
            self._create_timeline_view()

    def _create_card_view(self):
        """🎴 Kart görünümü oluştur"""
        canvas = tk.Canvas(self.events_container, bg=self.colors['secondary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.events_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Glass.TFrame")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        row, col = 0, 0
        for i, event in enumerate(self.filtered_events):
            card = self._create_event_card(scrollable_frame, event, row, col)
            
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def _create_event_card(self, parent, event, row, col):
        """🎴 Olay kartı oluştur"""
        card_frame = ttk.Frame(parent, style="Glass.TFrame")
        card_frame.grid(row=row, column=col, padx=8, pady=8, sticky="ew")
        
        card_canvas = tk.Canvas(card_frame, width=220, height=280, highlightthickness=0,
                              bg=self.colors['secondary'])
        card_canvas.pack(fill=tk.BOTH, expand=True)
        
        self._draw_rounded_rect(card_canvas, 5, 5, 215, 275, 12, self.colors['secondary'])
        
        timestamp = float(event.get("timestamp", 0))
        dt = datetime.datetime.fromtimestamp(timestamp)
        confidence = float(event.get("confidence", 0.0))
        
        date_str = dt.strftime("%d.%m.%Y")
        time_str = dt.strftime("%H:%M:%S")
        
        card_canvas.create_text(110, 25, text=date_str, font=("Segoe UI", 11, "bold"),
                              fill=self.colors['text'], anchor="center")
        card_canvas.create_text(110, 45, text=time_str, font=("Segoe UI", 9),
                              fill=self.colors['text_secondary'], anchor="center")
        
        conf_color = self._get_confidence_color(confidence)
        conf_text = f"{confidence*100:.1f}%"
        
        self._draw_circular_progress(card_canvas, 110, 90, 25, confidence, conf_color)
        card_canvas.create_text(110, 90, text=conf_text, font=("Segoe UI", 9, "bold"),
                              fill=self.colors['text'], anchor="center")
        
        thumb_rect = card_canvas.create_rectangle(15, 130, 205, 220,
                                                fill=self.colors['primary'],
                                                outline=conf_color, width=2)
        
        image_url = event.get("image_url")
        if image_url:
            self._load_thumbnail(card_canvas, image_url, 15, 130, 190, 90)
        else:
            card_canvas.create_text(110, 175, text="📷\nGörüntü Yok",
                                  font=("Segoe UI", 10), fill=self.colors['text_secondary'],
                                  anchor="center")
        
        btn_y = 240
        self._create_card_button(card_canvas, 45, btn_y, "👁️", lambda: self._view_event(event))
        self._create_card_button(card_canvas, 110, btn_y, "💾", lambda: self._save_event(event))
        self._create_card_button(card_canvas, 175, btn_y, "🗑️", lambda: self._delete_event(event))
        
        card_canvas.bind("<Button-1>", lambda e: self._select_event(event))
        
        return card_frame

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, radius, color):
        """🔘 Yuvarlatılmış dikdörtgen çizer"""
        canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    def _draw_circular_progress(self, canvas, x, y, radius, progress, color):
        """⭕ Dairesel progress çizer"""
        canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                         outline=self.colors['text_secondary'], width=2, fill="")
        
        extent = int(360 * progress)
        canvas.create_arc(x-radius, y-radius, x+radius, y+radius,
                        start=90, extent=-extent, outline=color, width=3,
                        style='arc')

    def _get_confidence_color(self, confidence):
        """🎨 Güven seviyesine göre renk döndürür"""
        if confidence >= 0.8:
            return self.colors['danger']
        elif confidence >= 0.6:
            return self.colors['warning']
        else:
            return self.colors['success']

    def _create_card_button(self, canvas, x, y, icon, command):
        """🔘 Kart butonu oluştur"""
        btn_bg = canvas.create_oval(x-12, y-12, x+12, y+12,
                                  fill=self.colors['accent'], outline="")
        btn_text = canvas.create_text(x, y, text=icon, font=("Segoe UI", 10),
                                    fill=self.colors['text'])
        
        canvas.tag_bind(btn_bg, "<Button-1>", lambda e: command())
        canvas.tag_bind(btn_text, "<Button-1>", lambda e: command())

    def _create_list_view(self):
        """📋 Liste görünümü oluştur"""
        style = ttk.Style()
        style.configure("Enhanced.Treeview",
                       background=self.colors['secondary'],
                       foreground=self.colors['text'],
                       fieldbackground=self.colors['secondary'],
                       font=("Segoe UI", 9))
        
        columns = ("date", "time", "confidence", "status")
        self.tree = ttk.Treeview(self.events_container, columns=columns, show="headings",
                               style="Enhanced.Treeview", height=12)
        
        headers = {"date": "📅 Tarih", "time": "⏰ Saat", "confidence": "🎯 Güven", "status": "📊 Durum"}
        for col, header in headers.items():
            self.tree.heading(col, text=header)
            self.tree.column(col, width=100, anchor="center")
        
        scrollbar = ttk.Scrollbar(self.events_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for event in self.filtered_events:
            timestamp = float(event.get("timestamp", 0))
            dt = datetime.datetime.fromtimestamp(timestamp)
            confidence = float(event.get("confidence", 0.0))
            
            status = "🔴 Yüksek" if confidence >= 0.8 else "🟡 Orta" if confidence >= 0.6 else "🟢 Düşük"
            
            self.tree.insert("", "end", values=(
                dt.strftime("%d.%m.%Y"),
                dt.strftime("%H:%M:%S"),
                f"{confidence*100:.1f}%",
                status
            ))
        
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _create_timeline_view(self):
        """⏱️ Zaman çizelgesi görünümü oluştur"""
        canvas = tk.Canvas(self.events_container, bg=self.colors['secondary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.events_container, orient="vertical", command=canvas.yview)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        y_pos = 40
        for event in sorted(self.filtered_events, key=lambda x: float(x.get("timestamp", 0)), reverse=True):
            timestamp = float(event.get("timestamp", 0))
            dt = datetime.datetime.fromtimestamp(timestamp)
            confidence = float(event.get("confidence", 0.0))
            
            color = self._get_confidence_color(confidence)
            canvas.create_oval(40, y_pos-4, 50, y_pos+4, fill=color, outline="")
            
            if y_pos > 40:
                canvas.create_line(45, y_pos-25, 45, y_pos-4, fill=self.colors['text_secondary'], width=2)
            
            canvas.create_text(60, y_pos-8, text=dt.strftime("%d.%m.%Y %H:%M:%S"),
                             font=("Segoe UI", 10, "bold"), fill=self.colors['text'], anchor="w")
            canvas.create_text(60, y_pos+4, text=f"Güven: {confidence*100:.1f}%",
                             font=("Segoe UI", 8), fill=color, anchor="w")
            
            y_pos += 50
        
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_search_change(self, event):
        """🔍 Arama değişikliği"""
        search_term = self.search_var.get().lower()
        self._filter_events(search_term)

    def _filter_events(self, search_term=""):
        """🔍 Olayları filtrele"""
        if not search_term:
            self.filtered_events = self.events.copy()
        else:
            self.filtered_events = []
            for event in self.events:
                timestamp = float(event.get("timestamp", 0))
                dt = datetime.datetime.fromtimestamp(timestamp)
                
                searchable_text = f"{dt.strftime('%d.%m.%Y %H:%M:%S')} {event.get('confidence', 0)*100:.1f}%"
                if search_term in searchable_text.lower():
                    self.filtered_events.append(event)
        
        self._update_events_display()

    def _advanced_search(self, event=None):
        """🔍 Gelişmiş arama fonksiyonu"""
        search_term = self.search_var.get().strip().lower()
        self._filter_events(search_term)

    def _apply_date_filter(self, selected_period):
        """📅 Tarih filtresi uygula"""
        now = datetime.datetime.now()
        
        if selected_period == "Bugün":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif selected_period == "Bu Hafta":
            start_date = now - datetime.timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif selected_period == "Bu Ay":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif selected_period == "Son 3 Ay":
            start_date = now - datetime.timedelta(days=90)
        else:
            self.filtered_events = self.events.copy()
            self._update_events_display()
            return
        
        start_timestamp = start_date.timestamp()
        self.filtered_events = [
            event for event in self.events
            if float(event.get("timestamp", 0)) >= start_timestamp
        ]
        self._update_events_display()

    def _apply_confidence_filter(self, value):
        """🎯 Güven filtresi uygula"""
        min_confidence = float(value) / 100
        self.filtered_events = [
            event for event in self.events
            if float(event.get("confidence", 0)) >= min_confidence
        ]
        self._update_events_display()

    def _load_events_with_stats(self):
        """📊 Olayları istatistiklerle birlikte yükle"""
        threading.Thread(target=self._load_events_thread, daemon=True).start()

    def _load_events_thread(self):
        """📊 Olayları yükleyen thread"""
        try:
            events = self.db_manager.get_fall_events(self.user["localId"], limit=100)
            self.events = events
            self.filtered_events = events
            
            self._calculate_statistics()
            self.after(0, self._update_ui_after_load)
            
        except Exception as e:
            logging.error(f"Events loading error: {e}")
            self.after(0, lambda: messagebox.showerror("Hata", f"Olaylar yüklenemedi: {e}"))

    def _calculate_statistics(self):
        """📊 İstatistikleri hesapla"""
        if not self.events:
            return
        
        now = datetime.datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        week_start = (now - datetime.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        
        self.stats = {
            "total_events": len(self.events),
            "high_confidence": len([e for e in self.events if float(e.get("confidence", 0)) >= 0.8]),
            "today_events": len([e for e in self.events if float(e.get("timestamp", 0)) >= today_start]),
            "this_week": len([e for e in self.events if float(e.get("timestamp", 0)) >= week_start]),
            "avg_confidence": sum(float(e.get("confidence", 0)) for e in self.events) / len(self.events) if self.events else 0.0
        }

    def _update_ui_after_load(self):
        """📊 Yükleme sonrası UI güncelle"""
        stats_data = [
            ("total_events", str(self.stats["total_events"])),
            ("high_confidence", str(self.stats["high_confidence"])),
            ("today_events", str(self.stats["today_events"])),
            ("avg_confidence", f"{self.stats['avg_confidence']*100:.1f}%")
        ]
        
        for i, (key, value) in enumerate(stats_data):
            if i < len(self.stats_cards):
                card = self.stats_cards[i]
        
        self._update_events_display()

    def _zoom_in(self):
        """🔍 Yakınlaştır"""
        self.zoom_level = min(5.0, self.zoom_level * 1.2)
        self._update_image_display()

    def _zoom_out(self):
        """🔍 Uzaklaştır"""
        self.zoom_level = max(0.1, self.zoom_level / 1.2)
        self._update_image_display()

    def _reset_image_view(self, event=None):
        """🔄 Görüntü zoom ve dönüşünü sıfırla"""
        self.zoom_level = 1.0
        self.rotation_angle = 0
        self._update_image_display()

    def _rotate_image(self):
        """↻ Görüntüyü döndür"""
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self._update_image_display()

    def _apply_filter(self):
        """🎨 Filtre uygula"""
        filters = list(self.image_filters.keys())
        current_index = filters.index(self.current_filter)
        next_index = (current_index + 1) % len(filters)
        self.current_filter = filters[next_index]
        self._update_image_display()

    def _save_image(self):
        """💾 Görüntüyü kaydet"""
        if not self.current_image:
            messagebox.showinfo("Bilgi", "Kaydedilecek görüntü yok")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg")]
        )
        
        if filename:
            try:
                self.current_image.save(filename)
                messagebox.showinfo("Başarılı", "Görüntü kaydedildi")
            except Exception as e:
                messagebox.showerror("Hata", f"Kaydetme hatası: {e}")

    def _export_image(self):
        """📤 Görüntüyü export et"""
        pass

    def _update_image_display(self):
        """🖼️ Görüntü görünümünü güncelle"""
        if not self.current_image:
            return
        
        img = self.current_image.copy()
        
        if self.rotation_angle != 0:
            img = img.rotate(self.rotation_angle, expand=True)
        
        if self.zoom_level != 1.0:
            new_size = (int(img.width * self.zoom_level), int(img.height * self.zoom_level))
            img = img.resize(new_size, Image.LANCZOS)
        
        img = self._apply_image_filter(img, self.current_filter)
        
        self.display_image = ImageTk.PhotoImage(img)
        self.image_canvas.delete("image")
        self.image_canvas.create_image(0, 0, anchor="nw", image=self.display_image, tags="image")
        
        self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))

    def _apply_image_filter(self, img, filter_name):
        """🎨 Görüntü filtresi uygula"""
        if filter_name == "enhance":
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.2)
        elif filter_name == "night_vision":
            img = img.convert("L")
            img = ImageEnhance.Brightness(img).enhance(1.5)
            img = img.convert("RGB")
        elif filter_name == "thermal":
            img = img.convert("L")
            img = img.convert("RGB")
        elif filter_name == "edge_detect":
            img = img.filter(ImageFilter.FIND_EDGES)
        
        return img

    def _view_event(self, event):
        """👁️ Olayı görüntüle"""
        self._select_event(event)

    def _save_event(self, event):
        """💾 Olayı kaydet"""
        pass

    def _delete_event(self, event):
        """🗑️ Olayı sil"""
        result = messagebox.askyesno("Onay", "Bu olayı silmek istediğinizden emin misiniz?")
        if result:
            try:
                self.db_manager.delete_fall_event(self.user["localId"], event.get("id"))
                self.events.remove(event)
                self.filtered_events.remove(event)
                self._update_events_display()
                messagebox.showinfo("Başarılı", "Olay silindi")
            except Exception as e:
                messagebox.showerror("Hata", f"Silme hatası: {e}")

    def _select_event(self, event):
        """📋 Olay seç"""
        image_url = event.get("image_url")
        if image_url:
            threading.Thread(target=self._load_image_for_viewer, args=(image_url,), daemon=True).start()
        
        self._update_event_metadata(event)

    def _load_image_for_viewer(self, url):
        """🖼️ Viewer için görüntü yükle"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            img_data = BytesIO(response.content)
            self.current_image = Image.open(img_data)
            
            self.after(0, self._update_image_display)
            
        except Exception as e:
            logging.error(f"Image loading error: {e}")

    def _update_event_metadata(self, event):
        """📊 Olay metadata'sını güncelle"""
        timestamp = float(event.get("timestamp", 0))
        dt = datetime.datetime.fromtimestamp(timestamp)
        confidence = float(event.get("confidence", 0.0))
        
        metadata = f"""📅 Tarih: {dt.strftime('%d.%m.%Y %H:%M:%S')}
🎯 Güven: {confidence*100:.2f}%
📷 Kamera: {event.get('camera_id', 'Bilinmiyor')}
🔍 Algılama: {event.get('detection_method', 'AI')}
📊 Track ID: {event.get('track_id', 'N/A')}
🆔 Event ID: {event.get('id', 'N/A')[:8]}...
"""
        
        self.metadata_text.delete(1.0, tk.END)
        self.metadata_text.insert(1.0, metadata)



    def _on_tree_select(self, event):
        """📋 Treeview'da bir öğe seçildiğinde çağrılır"""
        selected_items = self.tree.selection()
        if selected_items:
            # Seçilen ilk öğeyi al
            item = selected_items[0]
            # Öğenin değerlerini al (date, time, confidence, status)
            values = self.tree.item(item, "values")
            # Tarih ve saati birleştirerek timestamp oluştur
            timestamp_str = f"{values[0]} {values[1]}"  # Örn: "01.01.2025 12:00:00"
            try:
                # Olayı bulmak için timestamp ve güven skoru kullan
                timestamp = datetime.datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M:%S").timestamp()
                confidence = float(values[2].strip("%")) / 100  # Örn: "95.0%" -> 0.95
                # Eşleşen olayı filtered_events içinde ara
                for evt in self.filtered_events:
                    if abs(float(evt.get("timestamp", 0)) - timestamp) < 1 and abs(float(evt.get("confidence", 0)) - confidence) < 0.01:
                        self._select_event(evt)
                        break
            except (ValueError, IndexError) as e:
                logging.error(f"Treeview seçimi işlenirken hata: {e}")

    def _on_configure(self, event):
        """📐 Boyut değişikliği"""
        pass

    def _on_destroy(self, event):
        """🗑️ Widget yok edilmesi"""
        pass

    def _load_thumbnail(self, canvas, url, x, y, w, h):
        """🖼️ Thumbnail yükle"""
        canvas.create_text(x + w//2, y + h//2, text="🖼️\nYükleniyor...",
                         font=("Segoe UI", 9), fill=self.colors['text_secondary'])

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Enhanced History - Premium UI")
    root.geometry("1400x900")
    root.configure(bg="#121212")
    
    user = {"localId": "test_user", "email": "test@example.com"}
    
    class MockDB:
        def get_fall_events(self, user_id, limit=50):
            events = []
            for i in range(20):
                events.append({
                    "id": f"event_{i}",
                    "timestamp": time.time() - (i * 3600),
                    "confidence": 0.5 + (i % 5) * 0.1,
                    "camera_id": f"camera_{i % 3}",
                    "image_url": f"https://example.com/image_{i}.jpg"
                })
            return events
        
        def delete_fall_event(self, user_id, event_id):
            pass
    
    history_frame = HistoryFrame(root, user, MockDB(), lambda: root.quit())
    history_frame.pack(fill=tk.BOTH, expand=True)
    
    print("🚀 Enhanced History UI başlatıldı!")
    print("✨ Özellikler:")
    print("  🎨 4 Farklı Tema")
    print("  📊 İstatistik Dashboard")
    print("  🔍 Gelişmiş Arama")
    print("  🎴 Kart/Liste/Timeline Görünüm")
    print("  🖼️ Advanced Image Viewer")
    print("  🎬 Smooth Animasyonlar")
    
    root.mainloop()