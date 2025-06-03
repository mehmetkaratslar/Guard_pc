# =======================================================================================
# 📄 Dosya Adı: history.py
# 📁 Konum: guard_pc_app/ui/history.py
# 📌 Açıklama:
# Geçmiş düşme olaylarını listeleyen ve detaylarını gösteren modern, şık bir UI bileşeni.
# 403 Forbidden hatası düzeltildi, Firebase kimlik doğrulama token’ı eklendi.
# Optimize edilmiş versiyon - app.py ile uyumlu.
# 🔗 Bağlantılı Dosyalar:
# - ui/app.py, ui/dashboard.py, ui/settings.py (UI yönlendirme)
# - config/settings.py, utils/logger.py (tema ve loglama)
# - data/database.py (Firestore işlemleri)
# =======================================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import datetime
from PIL import Image, ImageTk, ImageEnhance
import requests
from io import BytesIO
import threading
import time
import sys
import os
import firebase_admin
from firebase_admin import auth

class HistoryFrame(ttk.Frame):
    """Modern ve premium görünümlü geçmiş olaylar ekranı."""

    def __init__(self, parent, user, db_manager, back_fn):
        """
        Args:
            parent (ttk.Frame): Üst çerçeve
            user (dict): Kullanıcı bilgileri
            db_manager (FirestoreManager): Veritabanı yönetici nesnesi
            back_fn (function): Geri dönüş fonksiyonu
        """
        super().__init__(parent, style="MainFrame.TFrame")
        
        self.user = user
        self.db_manager = db_manager
        self.back_fn = back_fn
        self.loading_animation_id = None
        self.events = []
        self.filtered_events = []
        self.image_cache = {}
        self.current_image = None
        
        self.dark_mode = self._get_theme_from_parent(parent)
        self._setup_colors()
        self._setup_styles()
        
        self._create_ui()
        
        self.zoom_level = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.dragging = False
        
        self._load_events()
        
        self.bind("<Configure>", self._on_configure)
        self.is_destroyed = False
        self.bind("<Destroy>", self._on_widget_destroy)

    def _get_theme_from_parent(self, parent):
        """Parent widget’tan tema durumunu alır."""
        try:
            app = self.winfo_toplevel()
            if hasattr(app, 'current_theme'):
                return app.current_theme == "dark"
        except:
            pass
        
        try:
            if sys.platform == "win32":
                import winreg
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return value == 0
        except:
            pass
            
        return False

    def _setup_colors(self):
        """Tema renklerini ayarlar."""
        if self.dark_mode:
            self.bg_color = "#121212"
            self.card_bg = "#1E1E1E"
            self.header_bg = "#252525"
            self.text_color = "#FFFFFF"
            self.text_secondary = "#AAAAAA"
            self.accent_color = "#3498db"
            self.accent_light = "#2980b9"
            self.success_color = "#2ecc71"
            self.warning_color = "#f39c12"
            self.danger_color = "#e74c3c"
            self.button_bg = "#333333"
            self.button_fg = "#FFFFFF"
            self.highlight_color = "#2d2d2d"
        else:
            self.bg_color = "#F8F9FA"
            self.card_bg = "#FFFFFF"
            self.header_bg = "#EAEAEA"
            self.text_color = "#333333"
            self.text_secondary = "#666666"
            self.accent_color = "#3498db"
            self.accent_light = "#5DADE2"
            self.success_color = "#2ecc71"
            self.warning_color = "#f39c12"
            self.danger_color = "#e74c3c"
            self.button_bg = "#EFEFEF"
            self.button_fg = "#333333"
            self.highlight_color = "#F0F0F0"

    def _setup_styles(self):
        """Uygulama stillerini oluşturur."""
        style = ttk.Style()
        
        style.configure("MainFrame.TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.card_bg, relief="flat")
        style.configure("Header.TFrame", background=self.header_bg)
        style.configure("Title.TLabel", 
                        background=self.header_bg,
                        foreground=self.text_color, 
                        font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabel", 
                        background=self.card_bg,
                        foreground=self.text_color, 
                        font=("Segoe UI", 14, "bold"))
        style.configure("TLabel", 
                        background=self.card_bg,
                        foreground=self.text_color, 
                        font=("Segoe UI", 11))
        style.configure("Info.TLabel", 
                        background=self.card_bg,
                        foreground=self.text_secondary, 
                        font=("Segoe UI", 10))
        style.configure("DetailHeader.TLabel", 
                        background=self.card_bg,
                        foreground=self.text_color, 
                        font=("Segoe UI", 12, "bold"))
        style.configure("DetailValue.TLabel", 
                        background=self.card_bg,
                        foreground=self.accent_color, 
                        font=("Segoe UI", 12))
        style.configure("TButton", 
                        background=self.button_bg,
                        foreground=self.button_fg,
                        font=("Segoe UI", 10), 
                        relief="flat")
        style.configure("Wide.TButton", 
                        background=self.accent_color,
                        foreground="white",
                        font=("Segoe UI", 10, "bold"))
        style.configure("Stop.TButton", 
                        background=self.danger_color,
                        foreground="white",
                        font=("Segoe UI", 10, "bold"))
        style.configure("Icon.TButton", 
                        background=self.card_bg,
                        foreground=self.text_color,
                        font=("Segoe UI", 14))
        style.configure("Treeview", 
                        background=self.card_bg,
                        foreground=self.text_color,
                        fieldbackground=self.card_bg,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading", 
                        background=self.header_bg,
                        foreground=self.text_color,
                        font=("Segoe UI", 10, "bold"),
                        relief="flat")
        style.map("Treeview",
                 background=[("selected", self.accent_color)],
                 foreground=[("selected", "white")])
        style.configure("Vertical.TScrollbar", 
                        background=self.card_bg,
                        troughcolor=self.bg_color)

    def _create_ui(self):
        """Modern UI bileşenlerini oluşturur."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)
        
        header_frame = ttk.Frame(self, style="Header.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        
        inner_header = ttk.Frame(header_frame, style="Header.TFrame", padding=15)
        inner_header.pack(fill=tk.X, expand=True)
        
        back_btn = ttk.Button(
            inner_header,
            text="← Geri",
            style="Wide.TButton",
            command=self.back_fn,
            width=10,
            cursor="hand2"
        )
        back_btn.pack(side=tk.LEFT, padx=5)
        
        title_label = ttk.Label(
            inner_header,
            text="Olay Geçmişi",
            style="Title.TLabel"
        )
        title_label.pack(side=tk.LEFT, padx=20)
        
        refresh_btn = ttk.Button(
            inner_header,
            text="⟳ Yenile",
            style="Wide.TButton",
            command=self._load_events,
            width=10,
            cursor="hand2"
        )
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        filter_frame = ttk.Frame(self, style="Card.TFrame")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=15)
        
        inner_filter = ttk.Frame(filter_frame, style="Card.TFrame", padding=15)
        inner_filter.pack(fill=tk.X, expand=True)
        
        date_frame = ttk.Frame(inner_filter, style="Card.TFrame")
        date_frame.pack(side=tk.LEFT, padx=(0, 20), fill=tk.Y)
        
        ttk.Label(
            date_frame,
            text="Tarih Filtresi:",
            style="TLabel"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.date_filter_var = tk.StringVar()
        date_entry = ttk.Entry(
            date_frame,
            textvariable=self.date_filter_var,
            width=12
        )
        date_entry.pack(side=tk.LEFT)
        date_entry.insert(0, "GG.AA.YYYY")
        date_entry.bind("<FocusIn>", lambda e: self._on_entry_focus_in(e, "GG.AA.YYYY"))
        date_entry.bind("<FocusOut>", lambda e: self._on_entry_focus_out(e, "GG.AA.YYYY"))
        
        conf_frame = ttk.Frame(inner_filter, style="Card.TFrame")
        conf_frame.pack(side=tk.LEFT, padx=(0, 20), fill=tk.Y)
        
        ttk.Label(
            conf_frame,
            text="Min. Olasılık (%):",
            style="TLabel"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.conf_filter_var = tk.StringVar()
        conf_entry = ttk.Entry(
            conf_frame,
            textvariable=self.conf_filter_var,
            width=6
        )
        conf_entry.pack(side=tk.LEFT)
        
        filter_btn = ttk.Button(
            inner_filter,
            text="Filtrele",
            style="Wide.TButton",
            command=self._apply_filters,
            width=10,
            cursor="hand2"
        )
        filter_btn.pack(side=tk.LEFT, padx=10)
        
        clear_btn = ttk.Button(
            inner_filter,
            text="Temizle",
            style="TButton",
            command=self._clear_filters,
            width=8,
            cursor="hand2"
        )
        clear_btn.pack(side=tk.LEFT)
        
        content_frame = ttk.Frame(self, style="Card.TFrame")
        content_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=4)
        content_frame.rowconfigure(0, weight=1)
        
        list_frame = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)
        
        list_header = ttk.Frame(list_frame, style="Card.TFrame")
        list_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(
            list_header,
            text="Algılanan Olaylar",
            style="Section.TLabel"
        ).pack(side=tk.LEFT)
        
        self.total_events_var = tk.StringVar(value="0 olay")
        ttk.Label(
            list_header,
            textvariable=self.total_events_var,
            style="Info.TLabel"
        ).pack(side=tk.RIGHT)
        
        list_container = ttk.Frame(list_frame, style="Card.TFrame")
        list_container.grid(row=1, column=0, sticky="nsew")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)
        
        self.event_list = ttk.Treeview(
            list_container,
            columns=("date", "time", "confidence"),
            show="headings",
            selectmode="browse",
            style="Treeview"
        )
        
        self.event_list.heading("date", text="Tarih", anchor="center")
        self.event_list.heading("time", text="Saat", anchor="center")
        self.event_list.heading("confidence", text="Olasılık", anchor="center")
        
        self.event_list.column("date", width=120, minwidth=100, anchor="center")
        self.event_list.column("time", width=100, minwidth=80, anchor="center")
        self.event_list.column("confidence", width=100, minwidth=80, anchor="center")
        
        list_scrollbar = ttk.Scrollbar(
            list_container, 
            orient=tk.VERTICAL, 
            command=self.event_list.yview,
            style="Vertical.TScrollbar"
        )
        self.event_list.configure(yscrollcommand=list_scrollbar.set)
        
        self.event_list.grid(row=0, column=0, sticky="nsew")
        list_scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.event_list.bind("<<TreeviewSelect>>", self._on_event_select)
        
        self.detail_frame = ttk.Frame(content_frame, style="Card.TFrame", padding=15)
        self.detail_frame.grid(row=0, column=1, sticky="nsew")
        self.detail_frame.columnconfigure(0, weight=1)
        self.detail_frame.rowconfigure(0, weight=0)
        self.detail_frame.rowconfigure(1, weight=0)
        self.detail_frame.rowconfigure(2, weight=0)
        self.detail_frame.rowconfigure(3, weight=1)
        
        detail_header = ttk.Frame(self.detail_frame, style="Card.TFrame")
        detail_header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        ttk.Label(
            detail_header,
            text="Olay Detayları",
            style="Section.TLabel"
        ).pack(side=tk.LEFT)
        
        info_frame = ttk.Frame(self.detail_frame, style="Card.TFrame")
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)
        info_frame.rowconfigure(0, weight=1)
        
        date_card = self._create_info_card(info_frame, "Tarih ve Saat")
        date_card.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.date_var = tk.StringVar(value="--.--.---- --:--:--")
        ttk.Label(
            date_card,
            textvariable=self.date_var,
            style="DetailValue.TLabel"
        ).pack(anchor=tk.CENTER, pady=10)
        
        conf_card = self._create_info_card(info_frame, "Düşme Olasılığı")
        conf_card.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
        self.conf_var = tk.StringVar(value="--.--")
        self.conf_label = ttk.Label(
            conf_card,
            textvariable=self.conf_var,
            style="DetailValue.TLabel"
        )
        self.conf_label.pack(anchor=tk.CENTER, pady=10)
        
        button_frame = ttk.Frame(self.detail_frame, style="Card.TFrame")
        button_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        
        export_btn = ttk.Button(
            button_frame,
            text="📷 Görüntüyü Kaydet",
            style="TButton",
            command=self._export_image,
            width=15,
            cursor="hand2"
        )
        export_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        delete_btn = ttk.Button(
            button_frame,
            text="🗑️ Olayı Sil",
            style="Stop.TButton",
            command=self._delete_event,
            width=12,
            cursor="hand2"
        )
        delete_btn.pack(side=tk.RIGHT)
        
        image_card = ttk.Frame(self.detail_frame, style="Card.TFrame")
        image_card.grid(row=3, column=0, sticky="nsew")
        image_card.columnconfigure(0, weight=1)
        image_card.rowconfigure(0, weight=0)
        image_card.rowconfigure(1, weight=1)
        
        img_header = ttk.Frame(image_card, style="Card.TFrame")
        img_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(
            img_header,
            text="Ekran Görüntüsü",
            style="DetailHeader.TLabel"
        ).pack(side=tk.LEFT)
        
        zoom_frame = ttk.Frame(img_header, style="Card.TFrame")
        zoom_frame.pack(side=tk.RIGHT)
        
        ttk.Button(
            zoom_frame,
            text="➖",
            style="Icon.TButton",
            command=self._zoom_out,
            width=3,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            zoom_frame,
            text="🔍",
            style="Icon.TButton",
            command=self._toggle_fullscreen,
            width=3,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            zoom_frame,
            text="➕",
            style="Icon.TButton",
            command=self._zoom_in,
            width=3,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)
        
        img_container = ttk.Frame(image_card, style="Card.TFrame", padding=2)
        img_container.grid(row=1, column=0, sticky="nsew")
        if not self.dark_mode:
            img_container["relief"] = "groove"
            img_container["borderwidth"] = 1
        
        self.image_frame = ttk.Frame(img_container, style="Card.TFrame")
        self.image_frame.pack(fill=tk.BOTH, expand=True)
        
        self.image_label = ttk.Label(
            self.image_frame,
            text="Görüntü yok",
            style="TLabel",
            anchor=tk.CENTER
        )
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        self.image_label.bind("<MouseWheel>", self._mouse_wheel)
        self.image_label.bind("<Button-1>", self._mouse_down)
        self.image_label.bind("<B1-Motion>", self._mouse_drag)
        self.image_label.bind("<ButtonRelease-1>", self._mouse_up)
        self.image_label.bind("<Double-Button-1>", lambda e: self._toggle_fullscreen())

    def _create_info_card(self, parent, title):
        """Bilgi kartı oluşturur."""
        card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        
        if self.dark_mode:
            card["borderwidth"] = 1
            card["relief"] = "solid"
        
        ttk.Label(
            card,
            text=title,
            style="DetailHeader.TLabel"
        ).pack(anchor=tk.CENTER)
        
        return card

    def _on_entry_focus_in(self, event, placeholder):
        """Giriş alanı odaklandığında placeholder’ı siler."""
        if event.widget.get() == placeholder:
            event.widget.delete(0, tk.END)

    def _on_entry_focus_out(self, event, placeholder):
        """Giriş alanı odak kaybettiğinde placeholder’ı ekler."""
        if event.widget.get() == "":
            event.widget.insert(0, placeholder)

    def _on_configure(self, event):
        """Pencere boyutu değiştiğinde düzeni günceller."""
        if event.widget == self and (event.width > 1 and event.height > 1):
            self.after(100, self._update_image_view)
    
    def _update_image_view(self):
        """Görüntüyü mevcut pencere boyutuna göre günceller."""
        if hasattr(self, "current_image") and self.current_image:
            self._display_image(self.current_image)
    
    def _clear_filters(self):
        """Filtreleri temizler ve tüm olayları gösterir."""
        self.date_filter_var.set("GG.AA.YYYY")
        self.conf_filter_var.set("")
        self.filtered_events = self.events
        self._update_event_list(self.events)
    
    def _load_events(self):
        """Olayları veritabanından asenkron olarak yükler."""
        try:
            self._start_loading_interface()
            threading.Thread(target=self._load_events_thread, daemon=True).start()
        except Exception as e:
            logging.error(f"Olaylar yüklenirken hata: {str(e)}")
            messagebox.showerror("Veri Yükleme Hatası", f"Olaylar yüklenemedi: {str(e)}")
    
    def _start_loading_interface(self):
        """Yükleniyor arayüzünü gösterir."""
        for item in self.event_list.get_children():
            self.event_list.delete(item)
        
        self.event_list.insert("", "end", values=("Yükleniyor...", "", ""))
        self._start_loading_animation()
        
        self.total_events_var.set("Yükleniyor...")
        self.date_var.set("--.--.---- --:--:--")
        self.conf_var.set("--.--")
        self.image_label.configure(text="Yükleniyor...", image="")
    
    def _start_loading_animation(self):
        """Yükleniyor animasyonunu başlatır."""
        if self.loading_animation_id:
            self.after_cancel(self.loading_animation_id)
        
        dots = [".", "..", "...", ""]
        dot_index = 0
        
        def animate():
            nonlocal dot_index
            try:
                children = self.event_list.get_children()
                if children:
                    self.event_list.item(children[0], values=(f"Yükleniyor{dots[dot_index]}", "", ""))
                    dot_index = (dot_index + 1) % len(dots)
                    self.loading_animation_id = self.after(300, animate)
            except Exception:
                self.loading_animation_id = None
        
        self.loading_animation_id = self.after(300, animate)
    
    def _stop_loading_animation(self):
        """Yükleniyor animasyonunu durdurur."""
        if self.loading_animation_id:
            self.after_cancel(self.loading_animation_id)
            self.loading_animation_id = None
    
    def _load_events_thread(self):
        """Olayları veritabanından yükleyen thread fonksiyonu."""
        try:
            events = self.db_manager.get_fall_events(self.user["localId"], limit=50)
            self.events = events
            self.filtered_events = events
            self.after(0, lambda: self._update_event_list(events))
        except Exception as e:
            logging.error(f"Olaylar yüklenirken thread hatası: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Veri Yükleme Hatası", f"Olaylar yüklenemedi: {str(e)}"))
    
    def _apply_filters(self):
        """Olayları tarih ve olasılık filtrelerine göre günceller."""
        try:
            date_filter = self.date_filter_var.get().strip()
            conf_filter = self.conf_filter_var.get().strip()
            
            if date_filter == "GG.AA.YYYY":
                date_filter = ""
            
            filtered = self.events.copy()
            filter_applied = False
            
            if date_filter:
                try:
                    filter_dt = datetime.datetime.strptime(date_filter, "%d.%m.%Y")
                    filtered = [
                        event for event in filtered
                        if datetime.datetime.fromtimestamp(float(event.get("timestamp", 0))).date() == filter_dt.date()
                    ]
                    filter_applied = True
                except ValueError:
                    self._show_error("Filtreleme Hatası", "Geçersiz tarih formatı. Örnek: 01.01.2025")
                    return
            
            if conf_filter:
                try:
                    conf_threshold = float(conf_filter) / 100
                    filtered = [
                        event for event in filtered
                        if float(event.get("confidence", 0.0)) >= conf_threshold
                    ]
                    filter_applied = True
                except ValueError:
                    self._show_error("Filtreleme Hatası", "Geçersiz olasılık değeri. Örnek: 50")
                    return
            
            self.filtered_events = filtered
            self._update_event_list(filtered)
            
            if filter_applied:
                message = f"{len(filtered)} olay filtrelendi."
                if len(filtered) == 0:
                    message = "Filtrelere uygun olay bulunamadı."
                self._show_info("Filtreleme", message)
                
        except Exception as e:
            logging.error(f"Filtreleme sırasında hata: {str(e)}")
            self._show_error("Filtreleme Hatası", f"Filtreleme başarısız: {str(e)}")
    
    def _update_event_list(self, events):
        """Olay listesini günceller."""
        try:
            self._stop_loading_animation()
            for item in self.event_list.get_children():
                self.event_list.delete(item)
            
            self.total_events_var.set(f"{len(events)} olay")
            
            if not events:
                self.event_list.insert("", "end", values=("Olay bulunamadı", "", ""))
                self.image_label.configure(text="Olay bulunamadı", image="")
                self.date_var.set("--.--.---- --:--:--")
                self.conf_var.set("--.--")
                return
            
            sorted_events = sorted(
                events, 
                key=lambda x: float(x.get("timestamp", 0)) if isinstance(x.get("timestamp"), (str, int, float)) else 0,
                reverse=True
            )
            
            for event in sorted_events:
                timestamp = float(event.get("timestamp", 0)) if isinstance(event.get("timestamp"), (str, int, float)) else 0
                dt = datetime.datetime.fromtimestamp(timestamp)
                date_str = dt.strftime("%d.%m.%Y")
                time_str = dt.strftime("%H:%M:%S")
                
                confidence = float(event.get("confidence", 0.0)) if isinstance(event.get("confidence"), (str, int, float)) else 0.0
                conf_str = f"%{confidence * 100:.2f}"
                
                tag = "normal"
                if confidence > 0.8:
                    tag = "high"
                elif confidence > 0.6:
                    tag = "medium"
                
                item_id = self.event_list.insert(
                    "", "end", text=event.get("id", ""), values=(date_str, time_str, conf_str), tags=(tag,)
                )
                
                if tag == "high":
                    self.event_list.tag_configure("high", background=self._adjust_color(self.danger_color, 0.2))
                elif tag == "medium":
                    self.event_list.tag_configure("medium", background=self._adjust_color(self.warning_color, 0.2))
            
            if self.event_list.get_children():
                first_item = self.event_list.get_children()[0]
                self.event_list.selection_set(first_item)
                self.event_list.focus(first_item)
                self._on_event_select(None)
                self.event_list.see(first_item)
                
        except Exception as e:
            logging.error(f"Olay listesi güncellenirken hata: {str(e)}")
            self._show_error("Liste Hatası", f"Olay listesi güncellenemedi: {str(e)}")
    
    def _on_event_select(self, event):
        """Bir olay seçildiğinde detayları gösterir."""
        try:
            selected = self.event_list.selection()
            if not selected:
                return
            
            item = selected[0]
            event_id = self.event_list.item(item, "text")
            
            selected_event = next((e for e in self.filtered_events if e.get("id") == event_id), None)
            
            if selected_event:
                self._show_event_details(selected_event)
            else:
                self.image_label.configure(text="Olay detayları bulunamadı", image="")
                self.date_var.set("--.--.---- --:--:--")
                self.conf_var.set("--.--")
                
        except Exception as e:
            logging.error(f"Olay seçilirken hata: {str(e)}")
            self._show_error("Detay Hatası", f"Olay detayları yüklenemedi: {str(e)}")
    
    def _delete_event(self):
        """Seçili olayı siler."""
        try:
            selected = self.event_list.selection()
            if not selected:
                self._show_info("Bilgi", "Lütfen silmek için bir olay seçin.")
                return
            
            item = selected[0]
            event_id = self.event_list.item(item, "text")
            
            result = messagebox.askyesno(
                "Onay", 
                "Bu olayı silmek istediğinizden emin misiniz?",
                icon=messagebox.WARNING
            )
            
            if not result:
                return
            
            self.event_list.item(item, values=("Siliniyor...", "", ""))
            self.after(500, lambda: self._complete_delete(event_id))
            
        except Exception as e:
            logging.error(f"Olay silinirken hata: {str(e)}")
            self._show_error("Silme Hatası", f"Olay silinemedi: {str(e)}")
    
    def _complete_delete(self, event_id):
        """Olay silme işlemini tamamlar."""
        try:
            self.db_manager.delete_fall_event(self.user["localId"], event_id)
            self.events = [e for e in self.events if e.get("id") != event_id]
            self.filtered_events = [e for e in self.filtered_events if e.get("id") != event_id]
            self._update_event_list(self.filtered_events)
            self._show_success("Başarılı", "Olay başarıyla silindi.")
            
        except Exception as e:
            logging.error(f"Olay silme işlemi tamamlanırken hata: {str(e)}")
            self._show_error("Silme Hatası", f"Olay silinemedi: {str(e)}")
    
    def _show_event_details(self, event):
        """Seçilen olayın detaylarını gösterir."""
        try:
            timestamp = float(event.get("timestamp", 0)) if isinstance(event.get("timestamp"), (str, int, float)) else 0
            dt = datetime.datetime.fromtimestamp(timestamp)
            self.date_var.set(dt.strftime("%d.%m.%Y %H:%M:%S"))
            
            confidence = float(event.get("confidence", 0.0)) if isinstance(event.get("confidence"), (str, int, float)) else 0.0
            conf_str = f"%{confidence * 100:.2f}"
            self.conf_var.set(conf_str)
            
            color = self.danger_color if confidence > 0.8 else self.warning_color if confidence > 0.6 else self.success_color
            self.conf_label.configure(foreground=color)
            
            image_url = event.get("image_url")
            if image_url:
                if image_url in self.image_cache:
                    self._display_image(self.image_cache[image_url])
                else:
                    self.image_label.configure(text="Görüntü yükleniyor...", image="")
                    threading.Thread(target=self._load_image, args=(image_url,), daemon=True).start()
            else:
                self.image_label.configure(text="Ekran görüntüsü bulunamadı", image="")
                self.current_image = None
                
        except Exception as e:
            logging.error(f"Olay detayları gösterilirken hata: {str(e)}")
            self.image_label.configure(text="Detaylar yüklenemedi", image="")
    
    def _load_image(self, url):
        """Güvenli görüntü yükleme."""
        try:
            # Firebase kimlik doğrulama token’ı al
            user = auth.get_user(self.user["localId"])
            id_token = firebase_admin.auth.create_custom_token(self.user["localId"]).decode('utf-8')
            headers = {"Authorization": f"Bearer {id_token}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            img_data = BytesIO(response.content)
            pil_img = Image.open(img_data)
            self.image_cache[url] = pil_img
            
            if not self.is_destroyed:
                self.after(0, lambda: self._display_image_with_animation(pil_img))
            
        except Exception as e:
            error_msg = f"Görüntü yüklenemedi: {str(e)}"
            logging.error(error_msg)
            if not self.is_destroyed and hasattr(self, 'image_label') and self.image_label.winfo_exists():
                self.after(0, lambda: self.image_label.configure(text=error_msg, image=""))
            self.current_image = None
    
    def _display_image_with_animation(self, pil_img):
        """Güvenli görüntü animasyonu."""
        if self.is_destroyed:
            return
            
        self.current_image = pil_img
        self.fade_alpha = 0.0
        
        def fade_step():
            if self.is_destroyed:
                return
                
            self.fade_alpha += 0.1
            if self.fade_alpha >= 1.0:
                self.fade_alpha = 1.0
                self._display_image(pil_img)
                return
            
            alpha_img = self._apply_fade(pil_img, self.fade_alpha)
            self._display_image(alpha_img)
            
            if not self.is_destroyed:
                self.after(30, fade_step)
        
        fade_step()
    
    def _display_image(self, pil_img):
        """Güvenli görüntü gösterimi."""
        try:
            if self.is_destroyed:
                return
                
            if not pil_img:
                self._safe_widget_operation(
                    self.image_label,
                    self.image_label.configure,
                    text="Görüntü yok",
                    image=""
                )
                return
            
            if not hasattr(self, 'original_width') or not self.original_width:
                self.original_width = pil_img.width
                self.original_height = pil_img.height
            
            img_width = int(self.original_width * self.zoom_level)
            img_height = int(self.original_height * self.zoom_level)
            
            if self.zoom_level != 1.0:
                resized_img = pil_img.resize((img_width, img_height), Image.LANCZOS)
            else:
                resized_img = pil_img.copy()
            
            if self.dark_mode:
                enhancer = ImageEnhance.Contrast(resized_img)
                resized_img = enhancer.enhance(1.1)
            
            tk_img = ImageTk.PhotoImage(resized_img)
            
            self._safe_widget_operation(
                self.image_label,
                self.image_label.configure,
                image=tk_img,
                text=""
            )
            self.image_label.image = tk_img
            
        except Exception as e:
            error_msg = f"Görüntü gösterilemiyor: {str(e)}"
            logging.error(error_msg)
            self._safe_widget_operation(
                self.image_label,
                self.image_label.configure,
                text=error_msg,
                image=""
            )

    def _apply_fade(self, img, alpha):
        """Görüntüye alfa karıştırma uygular."""
        try:
            enhancer = ImageEnhance.Brightness(img)
            return enhancer.enhance(alpha)
        except:
            return img
    
    def _zoom_in(self):
        """Görüntüyü yakınlaştırır."""
        if not self.current_image:
            return
        
        self.zoom_level = min(3.0, self.zoom_level + 0.25)
        self._display_image(self.current_image)
    
    def _zoom_out(self):
        """Görüntüyü uzaklaştırır."""
        if not self.current_image:
            return
        
        self.zoom_level = max(0.5, self.zoom_level - 0.25)
        self._display_image(self.current_image)
    
    def _toggle_fullscreen(self):
        """Görüntü detay panelini genişletir/daraltır."""
        if not self.current_image:
            return
        
        self.detail_panel_expanded = not getattr(self, 'detail_panel_expanded', False)
        
        if self.detail_panel_expanded:
            self.columnconfigure(0, weight=1)
            content_frame = self.winfo_children()[2]
            content_frame.columnconfigure(0, weight=0)
            content_frame.columnconfigure(1, weight=5)
            self.zoom_level = 1.5
            self._display_image(self.current_image)
        else:
            content_frame = self.winfo_children()[2]
            content_frame.columnconfigure(0, weight=3)
            content_frame.columnconfigure(1, weight=4)
            self.zoom_level = 1.0
            self._display_image(self.current_image)
    
    def _mouse_wheel(self, event):
        """Fare tekerleği ile zoom yapar."""
        if not self.current_image:
            return
        
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()
    
    def _mouse_down(self, event):
        """Fare tıklaması ile sürükleme başlangıcı."""
        if not self.current_image or self.zoom_level <= 1.0:
            return
        
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.dragging = True
    
    def _mouse_drag(self, event):
        """Fare sürüklemesi ile görüntüyü kaydırır."""
        if not self.dragging:
            return
        
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        self.image_offset_x += dx
        self.image_offset_y += dy
        
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        if self.current_image:
            self._display_image(self.current_image)
    
    def _mouse_up(self, event):
        """Fare bırakıldığında sürükleme sonlandırma."""
        self.dragging = False
    
    def _export_image(self):
        """Mevcut görüntüyü diske kaydeder."""
        if not self.current_image:
            self._show_info("Bilgi", "Kaydedilecek görüntü bulunamadı.")
            return
        
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("All files", "*.*")
                ],
                title="Görüntüyü Kaydet"
            )
            
            if filename:
                self.current_image.save(filename)
                self._show_success("Başarılı", f"Görüntü başarıyla kaydedildi:\n{filename}")
        except Exception as e:
            logging.error(f"Görüntü kaydedilirken hata: {str(e)}")
            self._show_error("Kaydetme Hatası", f"Görüntü kaydedilemedi: {str(e)}")
    
    def _show_error(self, title, message):
        """Hata mesajı gösterir."""
        messagebox.showerror(title, message)
    
    def _show_info(self, title, message):
        """Bilgi mesajı gösterir."""
        messagebox.showinfo(title, message)
    
    def _show_success(self, title, message):
        """Başarı mesajı gösterir."""
        messagebox.showinfo(title, message)
    
    def _adjust_color(self, hex_color, alpha):
        """Rengi belirtilen şeffaflık oranıyla karıştırır."""
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            
            if self.dark_mode:
                bg_r, bg_g, bg_b = 30, 30, 30
            else:
                bg_r, bg_g, bg_b = 255, 255, 255
            
            r = int(r * alpha + bg_r * (1 - alpha))
            g = int(g * alpha + bg_g * (1 - alpha))
            b = int(b * alpha + bg_b * (1 - alpha))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color
    
    def _on_widget_destroy(self, event):
        """Widget yok edildiğinde çağrılır."""
        if event.widget == self:
            self.is_destroyed = True
    
    def _safe_widget_operation(self, widget, operation, *args, **kwargs):
        """Widget operasyonlarını güvenli şekilde yapar."""
        try:
            if self.is_destroyed:
                return False
            if not widget.winfo_exists():
                return False
            return operation(*args, **kwargs)
        except tk.TclError as e:
            if "invalid command name" in str(e):
                logging.warning("Widget artık mevcut değil, operasyon iptal edildi")
                return False
            raise
    
    def destroy(self):
        """Güvenli widget yok etme."""
        try:
            self.is_destroyed = True
            if hasattr(self, 'loading_animation_id') and self.loading_animation_id:
                self.after_cancel(self.loading_animation_id)
            if hasattr(self, 'status_timer_id') and self.status_timer_id:
                self.after_cancel(self.status_timer_id)
            super().destroy()
        except Exception as e:
            logging.error(f"History frame destroy hatası: {str(e)}")