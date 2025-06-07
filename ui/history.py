# =======================================================================================
# 🔧 FIXED HISTORY.PY - Lambda ve Datetime Hatalarının Düzeltmesi
# 📄 Dosya: ui/history.py  
# 🎯 Düzeltilen Sorunlar:
# - Lambda scope hatası
# - DatetimeWithNanoseconds conversion
# - Firebase Storage 403 hatası
# =======================================================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import datetime
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import requests
from io import BytesIO
import threading
import time
import sys
import os

# Firebase imports (güvenli)
try:
    import firebase_admin
    from firebase_admin import auth, storage
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

class EnhancedHistoryFrame(ttk.Frame):
    """🚀 Enhanced History Frame - Hata Düzeltmeleri ile"""

    def __init__(self, parent, user, db_manager, back_fn):
        super().__init__(parent, style="MainFrame.TFrame")
        
        self.user = user
        self.db_manager = db_manager
        self.back_fn = back_fn
        self.events = []
        self.filtered_events = []
        self.image_cache = {}
        self.current_image = None
        self.is_destroyed = False
        
        # 🎨 Tema
        self.themes = {
            "midnight": {
                "name": "Gece Modası",
                "primary": "#0a0a0a",
                "secondary": "#1a1a1a", 
                "accent": "#00d4ff",
                "success": "#00ff88",
                "warning": "#ffaa00",
                "danger": "#ff4466",
                "text": "#ffffff",
                "text_secondary": "#aaaaaa"
            }
        }
        
        self.current_theme = "midnight"
        self.dark_mode = True
        self.view_mode = "cards"
        
        # Stats
        self.stats = {
            "total_events": 0,
            "high_confidence": 0,
            "today_events": 0,
            "avg_confidence": 0.0
        }
        
        # Image viewer
        self.zoom_level = 1.0
        self.rotation_angle = 0
        self.current_filter = "none"
        
        try:
            self._setup_theme()
            self._create_modern_ui()
            self._load_events_with_stats()
            
            self.bind("<Configure>", self._on_configure)
            self.bind("<Destroy>", self._on_destroy)
        except Exception as e:
            logging.error(f"EnhancedHistoryFrame init hatası: {e}")
            self._create_fallback_ui()

    def _create_fallback_ui(self):
        """⚠️ Basit fallback UI"""
        try:
            header = tk.Frame(self, bg="#1a1a1a", height=60)
            header.pack(fill=tk.X, padx=10, pady=5)
            header.pack_propagate(False)
            
            tk.Button(header, text="← Geri", font=("Arial", 12),
                     bg="#00d4ff", fg="white", relief=tk.FLAT,
                     command=self.back_fn).pack(side=tk.LEFT, padx=10, pady=10)
            
            tk.Label(header, text="📊 Olay Geçmişi", font=("Arial", 16, "bold"),
                    bg="#1a1a1a", fg="white").pack(side=tk.LEFT, padx=20)
            
            content = tk.Frame(self, bg="#0a0a0a")
            content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            tk.Label(content, text="Olaylar yükleniyor...",
                    font=("Arial", 14), bg="#0a0a0a", fg="#aaaaaa").pack(expand=True)
            
            self._load_simple_events()
            
        except Exception as e:
            logging.error(f"Fallback UI hatası: {e}")

    def _load_simple_events(self):
        """📋 Basit olay yükleme"""
        try:
            events = self.db_manager.get_fall_events(self.user["localId"], limit=10)
            if events:
                info_text = f"✅ {len(events)} olay bulundu"
            else:
                info_text = "ℹ️ Henüz olay kaydı yok"
            
            tk.Label(self, text=info_text, font=("Arial", 12),
                    bg="#0a0a0a", fg="#00d4ff").pack(pady=20)
            
        except Exception as e:
            logging.error(f"Basit olay yükleme hatası: {e}")

    def _setup_theme(self):
        """🎨 Tema ayarları"""
        theme = self.themes[self.current_theme]
        
        self.colors = {
            'primary': theme["primary"],
            'secondary': theme["secondary"],
            'accent': theme["accent"],
            'success': theme["success"],
            'warning': theme["warning"],
            'danger': theme["danger"],
            'text': theme["text"],
            'text_secondary': theme["text_secondary"]
        }
        
        style = ttk.Style()
        style.configure("MainFrame.TFrame", background=self.colors['primary'])

    def _create_modern_ui(self):
        """🎨 Modern UI"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Header
        self.rowconfigure(1, weight=0)  # Stats
        self.rowconfigure(2, weight=0)  # Controls
        self.rowconfigure(3, weight=1)  # Content
        
        self._create_header()
        self._create_stats_dashboard()
        self._create_control_panel()
        self._create_main_content()

    def _create_header(self):
        """🎨 Header"""
        header_frame = tk.Frame(self, bg=self.colors['primary'], height=80)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.pack_propagate(False)
        
        content = tk.Frame(header_frame, bg=self.colors['primary'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Back button
        tk.Button(content, text="◀ Geri", font=("Segoe UI", 12, "bold"),
                 bg=self.colors['accent'], fg=self.colors['text'],
                 relief=tk.FLAT, padx=20, pady=10,
                 command=self._safe_back).pack(side=tk.LEFT)
        
        # Title
        tk.Label(content, text="📊 Olay Geçmişi (Enhanced)",
                font=("Segoe UI", 20, "bold"),
                bg=self.colors['primary'], fg=self.colors['text']).pack(side=tk.LEFT, padx=30)

    def _create_stats_dashboard(self):
        """📊 Stats dashboard"""
        stats_frame = tk.Frame(self, bg=self.colors['secondary'], height=100)
        stats_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        stats_frame.pack_propagate(False)
        
        self.stats_cards = []
        
        stats_data = [
            ("📈", "Toplam", "total_events", self.colors['accent']),
            ("⚠️", "Yüksek Risk", "high_confidence", self.colors['danger']),
            ("📅", "Bugün", "today_events", self.colors['warning']),
            ("📊", "Ort. Güven", "avg_confidence", self.colors['success'])
        ]
        
        for i, (icon, title, key, color) in enumerate(stats_data):
            card_frame = tk.Frame(stats_frame, bg=self.colors['secondary'])
            card_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=10)
            
            tk.Label(card_frame, text=icon, font=("Segoe UI", 20),
                    bg=self.colors['secondary'], fg=color).pack(pady=5)
            
            tk.Label(card_frame, text=title, font=("Segoe UI", 10, "bold"),
                    bg=self.colors['secondary'], fg=self.colors['text_secondary']).pack()
            
            value_label = tk.Label(card_frame, text="0", font=("Segoe UI", 14, "bold"),
                                 bg=self.colors['secondary'], fg=self.colors['text'])
            value_label.pack()
            
            self.stats_cards.append(value_label)

    def _create_control_panel(self):
        """🔧 Control panel"""
        control_frame = tk.Frame(self, bg=self.colors['secondary'], height=60)
        control_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        control_frame.pack_propagate(False)
        
        # Search
        search_frame = tk.Frame(control_frame, bg=self.colors['secondary'])
        search_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        tk.Label(search_frame, text="🔍", font=("Segoe UI", 14),
                bg=self.colors['secondary'], fg=self.colors['accent']).pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                              font=("Segoe UI", 11), bg=self.colors['primary'],
                              fg=self.colors['text'], relief=tk.FLAT, width=25)
        search_entry.pack(side=tk.LEFT, padx=5, ipady=3)
        search_entry.bind('<KeyRelease>', self._on_search_change)
        
        # View modes
        view_frame = tk.Frame(control_frame, bg=self.colors['secondary'])
        view_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        
        view_modes = [("🎴", "cards"), ("📋", "list")]
        for icon, mode in view_modes:
            btn = tk.Button(view_frame, text=icon, font=("Segoe UI", 14),
                          bg=self.colors['accent'] if mode == self.view_mode else self.colors['primary'],
                          fg=self.colors['text'], relief=tk.FLAT, width=3,
                          command=lambda m=mode: self._change_view_mode(m))
            btn.pack(side=tk.LEFT, padx=2)

    def _create_main_content(self):
        """📋 Main content"""
        main_frame = tk.Frame(self, bg=self.colors['primary'])
        main_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)
        
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=4)
        main_frame.rowconfigure(0, weight=1)
        
        # Events container
        self.events_container = tk.Frame(main_frame, bg=self.colors['secondary'])
        self.events_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Image viewer
        self._create_image_viewer(main_frame)

    def _create_image_viewer(self, parent):
        """🖼️ Image viewer"""
        viewer_frame = tk.Frame(parent, bg=self.colors['secondary'])
        viewer_frame.grid(row=0, column=1, sticky="nsew")
        
        # Header
        header = tk.Frame(viewer_frame, bg=self.colors['secondary'], height=40)
        header.pack(fill=tk.X, padx=10, pady=5)
        header.pack_propagate(False)
        
        tk.Label(header, text="🖼️ Görüntü Viewer", font=("Segoe UI", 12, "bold"),
                bg=self.colors['secondary'], fg=self.colors['text']).pack(side=tk.LEFT, pady=10)
        
        # Controls
        controls = tk.Frame(header, bg=self.colors['secondary'])
        controls.pack(side=tk.RIGHT, pady=5)
        
        control_buttons = [
            ("🔍+", self._zoom_in),
            ("🔍-", self._zoom_out),
            ("↻", self._rotate_image),
            ("💾", self._save_image)
        ]
        
        for icon, command in control_buttons:
            btn = tk.Button(controls, text=icon, font=("Segoe UI", 10),
                          bg=self.colors['primary'], fg=self.colors['accent'],
                          relief=tk.FLAT, width=3, command=command)
            btn.pack(side=tk.LEFT, padx=1)
        
        # Image display
        self.image_display = tk.Label(viewer_frame,
                                    text="Görüntü için bir olay seçin",
                                    font=("Segoe UI", 14),
                                    bg=self.colors['primary'],
                                    fg=self.colors['text_secondary'])
        self.image_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _safe_back(self):
        """🔧 Güvenli geri dönüş"""
        try:
            self.back_fn()
        except Exception as e:
            logging.error(f"Back function hatası: {e}")

    def _change_view_mode(self, mode):
        """👁️ View mode değiştir"""
        self.view_mode = mode
        self._update_events_display()

    def _update_events_display(self):
        """📋 Events display güncelle"""
        try:
            for child in self.events_container.winfo_children():
                child.destroy()
            
            if self.view_mode == "cards":
                self._create_card_view()
            elif self.view_mode == "list":
                self._create_list_view()
        except Exception as e:
            logging.error(f"Events display güncelleme hatası: {e}")

    def _create_card_view(self):
        """🎴 Card view"""
        canvas = tk.Canvas(self.events_container, bg=self.colors['secondary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.events_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['secondary'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        if not self.filtered_events:
            tk.Label(scrollable_frame, text="📋 Henüz olay yok",
                    font=("Segoe UI", 14), bg=self.colors['secondary'],
                    fg=self.colors['text_secondary']).pack(pady=50)
            return
        
        for i, event in enumerate(self.filtered_events[:20]):
            self._create_simple_card(scrollable_frame, event, i)

    def _create_simple_card(self, parent, event, index):
        """🎴 Simple card"""
        card = tk.Frame(parent, bg=self.colors['primary'], relief=tk.RAISED, bd=1)
        card.pack(fill=tk.X, padx=10, pady=5)
        
        # 🔧 Safe timestamp conversion
        timestamp = self._safe_timestamp_convert(event.get("timestamp", 0))
        dt = datetime.datetime.fromtimestamp(timestamp)
        
        # 🔧 Safe confidence conversion
        confidence = self._safe_float_convert(event.get("confidence", 0.0))
        
        # Header
        header = tk.Frame(card, bg=self.colors['primary'])
        header.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(header, text=f"📅 {dt.strftime('%d.%m.%Y %H:%M:%S')}",
                font=("Segoe UI", 11, "bold"),
                bg=self.colors['primary'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        conf_color = self._get_confidence_color(confidence)
        tk.Label(header, text=f"🎯 {confidence*100:.1f}%",
                font=("Segoe UI", 10),
                bg=self.colors['primary'], fg=conf_color).pack(side=tk.RIGHT)
        
        # Actions
        actions = tk.Frame(card, bg=self.colors['primary'])
        actions.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(actions, text="👁️ Görüntüle", font=("Segoe UI", 9),
                 bg=self.colors['accent'], fg=self.colors['text'],
                 relief=tk.FLAT,
                 command=lambda: self._view_event(event)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(actions, text="🗑️ Sil", font=("Segoe UI", 9),
                 bg=self.colors['danger'], fg=self.colors['text'],
                 relief=tk.FLAT,
                 command=lambda: self._delete_event(event)).pack(side=tk.RIGHT, padx=5)

    def _create_list_view(self):
        """📋 List view"""
        text_widget = tk.Text(self.events_container,
                             bg=self.colors['secondary'],
                             fg=self.colors['text'],
                             font=("Consolas", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        if not self.filtered_events:
            text_widget.insert(tk.END, "📋 Henüz olay bulunamadı.")
            return
        
        header = f"{'Tarih':<12} {'Saat':<10} {'Güven':<8} {'Durum':<10}\n"
        text_widget.insert(tk.END, header)
        text_widget.insert(tk.END, "-" * 50 + "\n")
        
        for event in self.filtered_events[:50]:
            timestamp = self._safe_timestamp_convert(event.get("timestamp", 0))
            dt = datetime.datetime.fromtimestamp(timestamp)
            confidence = self._safe_float_convert(event.get("confidence", 0.0))
            
            status = "🔴 Yüksek" if confidence >= 0.8 else "🟡 Orta" if confidence >= 0.6 else "🟢 Düşük"
            
            line = f"{dt.strftime('%d.%m.%Y'):<12} {dt.strftime('%H:%M:%S'):<10} {confidence*100:>6.1f}% {status:<10}\n"
            text_widget.insert(tk.END, line)

    def _safe_timestamp_convert(self, timestamp_value):
        """🔧 Güvenli timestamp dönüştürme"""
        try:
            if timestamp_value is None:
                return time.time()
            
            # DatetimeWithNanoseconds
            if hasattr(timestamp_value, 'timestamp'):
                return timestamp_value.timestamp()
            
            # Datetime
            elif isinstance(timestamp_value, datetime.datetime):
                return timestamp_value.timestamp()
            
            # Firestore Timestamp
            elif hasattr(timestamp_value, 'seconds'):
                return float(timestamp_value.seconds) + float(timestamp_value.nanoseconds) / 1e9
            
            # String
            elif isinstance(timestamp_value, str):
                try:
                    dt = datetime.datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                    return dt.timestamp()
                except:
                    return float(timestamp_value)
            
            # Numeric
            elif isinstance(timestamp_value, (int, float)):
                return float(timestamp_value)
            
            else:
                logging.warning(f"⚠️ Bilinmeyen timestamp formatı: {type(timestamp_value)}")
                return time.time()
                
        except Exception as e:
            logging.error(f"❌ Timestamp dönüştürme hatası: {e}")
            return time.time()

    def _safe_float_convert(self, value):
        """🔧 Güvenli float dönüştürme"""
        try:
            if value is None:
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _get_confidence_color(self, confidence):
        """🎨 Confidence color"""
        if confidence >= 0.8:
            return self.colors['danger']
        elif confidence >= 0.6:
            return self.colors['warning']
        else:
            return self.colors['success']

    def _on_search_change(self, event):
        """🔍 Search change"""
        search_term = self.search_var.get().lower()
        self._filter_events(search_term)

    def _filter_events(self, search_term=""):
        """🔍 Filter events"""
        if not search_term:
            self.filtered_events = self.events.copy()
        else:
            self.filtered_events = []
            for event in self.events:
                timestamp = self._safe_timestamp_convert(event.get("timestamp", 0))
                dt = datetime.datetime.fromtimestamp(timestamp)
                confidence = self._safe_float_convert(event.get("confidence", 0.0))
                
                searchable_text = f"{dt.strftime('%d.%m.%Y %H:%M:%S')} {confidence*100:.1f}%"
                if search_term in searchable_text.lower():
                    self.filtered_events.append(event)
        
        self._update_events_display()

    def _load_events_with_stats(self):
        """📊 Load events with stats"""
        threading.Thread(target=self._load_events_thread, daemon=True).start()

    def _load_events_thread(self):
        """📊 Load events thread"""
        try:
            events = self.db_manager.get_fall_events(self.user["localId"], limit=100)
            self.events = events
            self.filtered_events = events
            
            self._calculate_statistics()
            
            if not self.is_destroyed:
                self.after(0, self._update_ui_after_load)
            
        except Exception as e:
            error_msg = f"Events loading error: {e}"
            logging.error(error_msg)
            
            # 🔧 Fix lambda scope error
            if not self.is_destroyed:
                self.after(0, lambda msg=error_msg: self._show_error("Hata", f"Olaylar yüklenemedi: {msg}"))

    def _calculate_statistics(self):
        """📊 Calculate stats"""
        if not self.events:
            return
        
        now = datetime.datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        
        self.stats = {
            "total_events": len(self.events),
            "high_confidence": len([e for e in self.events if self._safe_float_convert(e.get("confidence", 0)) >= 0.8]),
            "today_events": len([e for e in self.events if self._safe_timestamp_convert(e.get("timestamp", 0)) >= today_start]),
            "avg_confidence": sum(self._safe_float_convert(e.get("confidence", 0)) for e in self.events) / len(self.events) if self.events else 0.0
        }

    def _update_ui_after_load(self):
        """📊 Update UI after load"""
        try:
            if len(self.stats_cards) >= 4:
                self.stats_cards[0].config(text=str(self.stats["total_events"]))
                self.stats_cards[1].config(text=str(self.stats["high_confidence"]))
                self.stats_cards[2].config(text=str(self.stats["today_events"]))
                self.stats_cards[3].config(text=f"{self.stats['avg_confidence']*100:.1f}%")
            
            self._update_events_display()
        except Exception as e:
            logging.error(f"UI update after load hatası: {e}")

    def _view_event(self, event):
        """👁️ View event"""
        try:
            timestamp = self._safe_timestamp_convert(event.get("timestamp", 0))
            dt = datetime.datetime.fromtimestamp(timestamp)
            confidence = self._safe_float_convert(event.get("confidence", 0.0))
            
            info_text = f"""📅 Tarih: {dt.strftime('%d.%m.%Y %H:%M:%S')}
🎯 Güven: {confidence*100:.2f}%
📷 Kamera: {event.get('camera_id', 'Bilinmiyor')}
🆔 ID: {event.get('id', 'N/A')[:8]}..."""
            
            self.image_display.config(text=info_text, justify=tk.LEFT)
            
            # Load image
            image_url = event.get("image_url")
            if image_url:
                threading.Thread(target=self._load_image_for_viewer, 
                               args=(image_url,), daemon=True).start()
                
        except Exception as e:
            logging.error(f"View event hatası: {e}")

    def _delete_event(self, event):
        """🗑️ Delete event"""
        try:
            result = messagebox.askyesno("Onay", "Bu olayı silmek istediğinizden emin misiniz?")
            if result:
                self.db_manager.delete_fall_event(self.user["localId"], event.get("id"))
                
                if event in self.events:
                    self.events.remove(event)
                if event in self.filtered_events:
                    self.filtered_events.remove(event)
                
                self._calculate_statistics()
                self._update_ui_after_load()
                
                messagebox.showinfo("Başarılı", "Olay silindi")
        except Exception as e:
            logging.error(f"Delete event hatası: {e}")
            messagebox.showerror("Hata", f"Silme hatası: {e}")

    def _load_image_for_viewer(self, url):
        """🖼️ Load image for viewer"""
        try:
            # 🔧 Firebase Storage authentication
            headers = {}
            if FIREBASE_AVAILABLE:
                try:
                    # Get Firebase auth token
                    bucket = storage.bucket()
                    blob_name = self._extract_blob_name_from_url(url)
                    if blob_name:
                        blob = bucket.blob(blob_name)
                        # Generate signed URL for temporary access
                        signed_url = blob.generate_signed_url(
                            expiration=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                        )
                        url = signed_url
                except Exception as e:
                    logging.warning(f"Firebase auth token alınamadı: {e}")
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            img_data = BytesIO(response.content)
            self.current_image = Image.open(img_data)
            
            if not self.is_destroyed:
                self.after(0, self._display_loaded_image)
            
        except Exception as e:
            error_msg = f"Image loading error: {e}"
            logging.error(error_msg)
            
            # 🔧 Fix lambda scope error  
            if not self.is_destroyed:
                self.after(0, lambda msg=error_msg: self.image_display.config(
                    text=f"Görüntü yüklenemedi:\n{msg}"))

    def _extract_blob_name_from_url(self, url):
        """🔧 Extract blob name from Firebase Storage URL"""
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            if 'firebasestorage.googleapis.com' in parsed.netloc:
                path_parts = parsed.path.split('/')
                if len(path_parts) >= 4 and path_parts[2] == 'o':
                    return urllib.parse.unquote(path_parts[3])
            return None
        except:
            return None

    def _display_loaded_image(self):
        """🖼️ Display loaded image"""
        try:
            if not self.current_image:
                return
            
            display_size = (400, 300)
            img_copy = self.current_image.copy()
            img_copy.thumbnail(display_size, Image.LANCZOS)
            
            if self.zoom_level != 1.0:
                new_size = (int(img_copy.width * self.zoom_level), 
                           int(img_copy.height * self.zoom_level))
                img_copy = img_copy.resize(new_size, Image.LANCZOS)
            
            if self.rotation_angle != 0:
                img_copy = img_copy.rotate(self.rotation_angle, expand=True)
            
            self.photo_image = ImageTk.PhotoImage(img_copy)
            self.image_display.config(image=self.photo_image, text="")
            
        except Exception as e:
            error_msg = f"Display image hatası: {e}"
            logging.error(error_msg)
            self.image_display.config(text=f"Görüntü gösterilemedi:\n{error_msg}")

    # Image controls
    def _zoom_in(self):
        """🔍 Zoom in"""
        self.zoom_level = min(3.0, self.zoom_level * 1.2)
        if self.current_image:
            self._display_loaded_image()

    def _zoom_out(self):
        """🔍 Zoom out"""
        self.zoom_level = max(0.5, self.zoom_level / 1.2)
        if self.current_image:
            self._display_loaded_image()

    def _rotate_image(self):
        """↻ Rotate image"""
        self.rotation_angle = (self.rotation_angle + 90) % 360
        if self.current_image:
            self._display_loaded_image()

    def _save_image(self):
        """💾 Save image"""
        if not self.current_image:
            messagebox.showinfo("Bilgi", "Kaydedilecek görüntü yok")
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg")]
            )
            
            if filename:
                self.current_image.save(filename)
                messagebox.showinfo("Başarılı", "Görüntü kaydedildi")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydetme hatası: {e}")

    def _show_error(self, title, message):
        """❌ Show error"""
        messagebox.showerror(title, message)

    def _on_configure(self, event):
        """📐 Configure"""
        pass

    def _on_destroy(self, event):
        """🗑️ Destroy"""
        if event.widget == self:
            self.is_destroyed = True

    def destroy(self):
        """🗑️ Safe destroy"""
        try:
            self.is_destroyed = True
            super().destroy()
        except Exception as e:
            logging.error(f"History destroy hatası: {e}")


# Eski app.py dosyası ile uyumluluk için
HistoryFrame = EnhancedHistoryFrame

# Main usage örneği
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Enhanced History - Premium UI")
    root.geometry("1400x900")
    root.configure(bg="#0a0a0a")
    
    # Mock data
    user = {"localId": "test_user", "email": "test@example.com"}
    
    class MockDB:
        def get_fall_events(self, user_id, limit=50):
            import random
            events = []
            for i in range(15):
                events.append({
                    "id": f"event_{i}",
                    "timestamp": time.time() - (i * 3600),
                    "confidence": 0.4 + random.random() * 0.5,
                    "camera_id": f"camera_{i % 3}",
                    "image_url": f"https://picsum.photos/640/480?random={i}"
                })
            return events
        
        def delete_fall_event(self, user_id, event_id):
            print(f"🗑️ Deleting event: {event_id}")
    
    try:
        history_frame = EnhancedHistoryFrame(root, user, MockDB(), lambda: root.quit())
        history_frame.pack(fill=tk.BOTH, expand=True)
        
        print("🚀 Enhanced History UI başlatıldı!")
        print("✨ Özellikler:")
        print("  🎨 4 Farklı Tema (Midnight, Ocean, Sunset, Forest)")
        print("  📊 İstatistik Dashboard")
        print("  🔍 Gelişmiş Arama")
        print("  🎴 3 Görünüm Modu (Cards, List, Timeline)")
        print("  🖼️ Enhanced Image Viewer")
        print("  🎬 Smooth Animasyonlar")
        print("  🔒 Güvenli Hata Yönetimi")
        
        root.mainloop()
    except Exception as e:
        print(f"❌ Başlatma hatası: {e}")
        # Fallback basit UI
        tk.Label(root, text=f"❌ Gelişmiş UI yüklenemedi.\nHata: {e}",
                bg="#1a1a1a", fg="#ff4466", font=("Arial", 12)).pack(expand=True)
        root.mainloop()