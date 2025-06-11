# =======================================================================================
# DÜZELTME: Model değiştirme ve test bildirimi sistemi - TAM ENTEGRESYİON
# Çözüm: AI model değiştirme fonksiyonu app.py ile entegre edildi
# =======================================================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import logging
import threading
import time
import glob
import uuid
import numpy as np
from datetime import datetime
from PIL import Image, ImageTk

class EnhancedSettingsFrame(tk.Frame):
    """
    DÜZELTME: Ultra gelişmiş ayarlar frame'i - AI model değiştirme sistemi ile
    app.py ile tam entegre
    """

    def __init__(self, parent, user, db_manager, back_fn, fall_detector=None, app_instance=None):
        """
        DÜZELTME: app_instance parametresi eklendi
        
        Args:
            parent: Üst widget
            user: Kullanıcı bilgileri
            db_manager: Veritabanı yöneticisi
            back_fn: Geri dönüş fonksiyonu
            fall_detector: FallDetector instance
            app_instance: Ana GuardApp instance
        """
        super().__init__(parent)
        
        self.user = user
        self.db_manager = db_manager
        self.back_fn = back_fn
        self.fall_detector = fall_detector
        self.app_instance = app_instance  # DÜZELTME: App referansı
        
        # Canvas referansı scroll hatası için
        self.canvas = None
        
        # Kullanıcı ayarlarını yükle
        try:
            self.user_data = self.db_manager.get_user_data(user["localId"])
            self.settings = self.user_data.get("settings", {}) if self.user_data else {}
            logging.info(f"✅ Kullanıcı ayarları yüklendi: {len(self.settings)} ayar")
        except Exception as e:
            logging.error(f"❌ Kullanıcı ayarları yükleme hatası: {e}")
            self.user_data = {}
            self.settings = {}
        
        # Model directory
        self.model_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "models")
        
        # Available models scan
        self.available_models = self._scan_available_models()
        
        # Tema ve stil ayarları
        self.dark_mode = self.settings.get("dark_mode", False)
        self._setup_colors()
        self._setup_styles()
        
        # UI değişkenleri
        self._setup_variables()
        
        # UI oluştur
        self._create_enhanced_ui()
        
        # Değişiklik takibi
        self.is_modified = False
        
        # Kamera referansları (ana uygulamadan alınacak)
        self.cameras = self._get_camera_references()

    def destroy(self):
        """Widget'ı temizle."""
        try:
            # Mouse wheel binding'ini temizle
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.unbind_all("<MouseWheel>")
        except:
            pass
        super().destroy()

    def _scan_available_models(self):
        """Mevcut model dosyalarını tara."""
        models = {}
        
        try:
            if not os.path.exists(self.model_directory):
                os.makedirs(self.model_directory, exist_ok=True)
                logging.info(f"📁 Model dizini oluşturuldu: {self.model_directory}")
            
            # .pt dosyalarını ara
            model_files = glob.glob(os.path.join(self.model_directory, "*.pt"))
            
            # Model bilgileri
            model_info = {
                "yolo11n-pose": {"name": "YOLOv11 Nano Pose", "size": "~6MB", "speed": "En Hızlı", "accuracy": "Düşük"},
                "yolo11s-pose": {"name": "YOLOv11 Small Pose", "size": "~22MB", "speed": "Hızlı", "accuracy": "Orta"},
                "yolo11m-pose": {"name": "YOLOv11 Medium Pose", "size": "~52MB", "speed": "Orta", "accuracy": "İyi"},
                "yolo11l-pose": {"name": "YOLOv11 Large Pose", "size": "~110MB", "speed": "Yavaş", "accuracy": "Yüksek"},
                "yolo11x-pose": {"name": "YOLOv11 Extra Large Pose", "size": "~220MB", "speed": "En Yavaş", "accuracy": "En Yüksek"}
            }
            
            for model_file in model_files:
                model_name = os.path.basename(model_file).replace('.pt', '')
                file_size = os.path.getsize(model_file) / (1024 * 1024)  # MB
                
                model_data = model_info.get(model_name, {
                    "name": model_name.title(),
                    "size": f"~{file_size:.1f}MB",
                    "speed": "Bilinmiyor",
                    "accuracy": "Bilinmiyor"
                })
                
                models[model_name] = {
                    **model_data,
                    "path": model_file,
                    "file_size_mb": file_size,
                    "exists": True
                }
            
            # Eksik modelleri de listele (indirilebilir)
            for model_name, info in model_info.items():
                if model_name not in models:
                    models[model_name] = {
                        **info,
                        "path": os.path.join(self.model_directory, f"{model_name}.pt"),
                        "file_size_mb": 0,
                        "exists": False
                    }
            
            logging.info(f"🤖 Model tarama tamamlandı: {len(model_files)} model bulundu")
            
        except Exception as e:
            logging.error(f"❌ Model tarama hatası: {e}")
        
        return models

    def _get_camera_references(self):
        """Ana uygulamadan kamera referanslarını al."""
        try:
            # DÜZELTME: Önce app_instance'dan dene
            if self.app_instance and hasattr(self.app_instance, 'cameras'):
                return self.app_instance.cameras
            
            # Widget hiyerarşisinde yukarı çıkarak ana uygulamayı bul
            widget = self.master
            while widget:
                if hasattr(widget, 'cameras'):
                    return widget.cameras
                widget = widget.master
            return []
        except:
            return []

    def _setup_colors(self):
        """Tema renkleri."""
        if self.dark_mode:
            self.colors = {
                'bg_primary': "#121212",
                'bg_secondary': "#1E1E1E", 
                'bg_tertiary': "#2A2A2A",
                'accent_primary': "#3498db",
                'accent_secondary': "#2ecc71",
                'accent_danger': "#e74c3c",
                'accent_warning': "#f39c12",
                'text_primary': "#FFFFFF",
                'text_secondary': "#B0BEC5",
                'border': "#555555"
            }
        else:
            self.colors = {
                'bg_primary': "#FFFFFF",
                'bg_secondary': "#F8F9FA",
                'bg_tertiary': "#E9ECEF",
                'accent_primary': "#3498db",
                'accent_secondary': "#2ecc71", 
                'accent_danger': "#e74c3c",
                'accent_warning': "#f39c12",
                'text_primary': "#2C3E50",
                'text_secondary': "#6C757D",
                'border': "#DEE2E6"
            }

    def _setup_styles(self):
        """TTK stilleri."""
        style = ttk.Style()
        
        # Ana çerçeve
        style.configure("Settings.TFrame", background=self.colors['bg_primary'])
        
        # Kartlar
        style.configure("Card.TFrame", background=self.colors['bg_secondary'], relief="flat")
        
        # Başlıklar
        style.configure("Title.TLabel", 
                       background=self.colors['accent_primary'],
                       foreground="#FFFFFF", 
                       font=("Segoe UI", 16, "bold"))
        
        style.configure("Section.TLabel",
                       background=self.colors['bg_secondary'],
                       foreground=self.colors['text_primary'],
                       font=("Segoe UI", 14, "bold"))

    def _setup_variables(self):
        """UI değişkenlerini ayarla."""
        # Kullanıcı bilgileri
        self.name_var = tk.StringVar(value=self.user.get("displayName", ""))
        self.email_var = tk.StringVar(value=self.user.get("email", ""))
        
        # Bildirim ayarları
        self.email_notification_var = tk.BooleanVar(value=self.settings.get("email_notification", True))
        self.sms_notification_var = tk.BooleanVar(value=self.settings.get("sms_notification", False))
        self.phone_var = tk.StringVar(value=self.settings.get("phone_number", ""))
        self.fcm_notification_var = tk.BooleanVar(value=self.settings.get("fcm_notification", True))
        
        # Tema ayarları
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        
        # AI Model ayarları
        self.selected_model_var = tk.StringVar()
        current_model = self._get_current_model_name()
        if current_model in self.available_models:
            self.selected_model_var.set(current_model)
        
        # Kamera ayarları
        self.auto_brightness_var = tk.BooleanVar(value=self.settings.get("auto_brightness", True))
        self.brightness_var = tk.IntVar(value=self.settings.get("brightness_adjustment", 0))
        self.contrast_var = tk.DoubleVar(value=self.settings.get("contrast_adjustment", 1.0))
        
        # Düşme algılama hassasiyet
        self.sensitivity_var = tk.StringVar(value=self.settings.get("fall_sensitivity", "medium"))

    def _get_current_model_name(self):
        """DÜZELTME: Mevcut model adını al."""
        try:
            # Önce app_instance'dan dene
            if self.app_instance and hasattr(self.app_instance, 'system_state'):
                current_model = self.app_instance.system_state.get('current_model')
                if current_model:
                    return current_model
            
            # Fall detector'dan dene
            if self.fall_detector and hasattr(self.fall_detector, 'model_path'):
                model_file = os.path.basename(self.fall_detector.model_path)
                return model_file.replace('.pt', '')
            
            # Settings'den dene
            return self.settings.get('selected_ai_model', 'yolo11l-pose')
            
        except Exception as e:
            logging.error(f"❌ Current model name alınamadı: {e}")
            return 'yolo11l-pose'

    def _create_enhanced_ui(self):
        """Gelişmiş UI oluştur."""
        self.configure(bg=self.colors['bg_primary'])
        
        # Grid layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Header
        self.rowconfigure(1, weight=1)  # Content
        
        # Header
        self._create_header()
        
        # Scrollable content
        self._create_scrollable_content()

    def _create_header(self):
        """Header oluştur."""
        header = tk.Frame(self, bg=self.colors['accent_primary'], height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        
        # Header içerik
        header_content = tk.Frame(header, bg=self.colors['accent_primary'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Geri butonu
        back_btn = tk.Button(header_content,
                            text="← Geri",
                            font=("Segoe UI", 12, "bold"),
                            bg="#FFFFFF",
                            fg=self.colors['accent_primary'],
                            relief=tk.FLAT,
                            padx=15, pady=8,
                            command=self._on_back,
                            cursor="hand2")
        back_btn.pack(side=tk.LEFT)
        
        # Başlık
        title_label = tk.Label(header_content,
                              text="⚙️ Gelişmiş Ayarlar",
                              font=("Segoe UI", 18, "bold"),
                              fg="#FFFFFF",
                              bg=self.colors['accent_primary'])
        title_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Kaydet butonu
        save_btn = tk.Button(header_content,
                            text="💾 Kaydet",
                            font=("Segoe UI", 12, "bold"),
                            bg=self.colors['accent_secondary'],
                            fg="#FFFFFF",
                            relief=tk.FLAT,
                            padx=15, pady=8,
                            command=self._save_settings,
                            cursor="hand2")
        save_btn.pack(side=tk.RIGHT)

    def _create_scrollable_content(self):
        """Scrollable içerik oluştur."""
        # Canvas ve scrollbar
        self.canvas = tk.Canvas(self, bg=self.colors['bg_primary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scrollable_frame = tk.Frame(self.canvas, bg=self.colors['bg_primary'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grid
        self.canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        
        # İçerik kartları
        self._create_content_cards(scrollable_frame)
        
        # Mouse wheel scroll - güvenli versiyon
        def _on_mousewheel(event):
            try:
                if self.canvas and self.canvas.winfo_exists():
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                pass  # Widget destroyed, ignore
        
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _create_content_cards(self, parent):
        """İçerik kartlarını 2 sütunlu olarak oluştur."""
        # Grid yapısı oluştur
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        # Sol frame (sütun 0)
        sol_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        sol_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        # Sağ frame (sütun 1)
        sag_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        sag_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Sol sütuna ana ayarlar
        self._create_user_info_card(sol_frame)
        self._create_ai_model_card(sol_frame)
        self._create_camera_settings_card(sol_frame)

        # Sağ sütuna: Düşme Algılama + Tema
        self._create_fall_detection_card(sag_frame)
        self._create_appearance_card(sag_frame)
        self._create_notification_card(sag_frame)

    def _create_user_info_card(self, parent):
        """Kullanıcı bilgileri kartı."""
        card = self._create_card(parent, "👤 Kullanıcı Bilgileri")
        
        # Ad Soyad
        self._create_input_field(card, "Ad Soyad:", self.name_var)
        
        # E-posta (readonly)
        self._create_input_field(card, "E-posta:", self.email_var, readonly=True)

    def _create_ai_model_card(self, parent):
        """DÜZELTME: AI Model yönetimi kartı - app.py entegrasyonu ile."""
        card = self._create_card(parent, "🤖 AI Model Yönetimi")
        
        # Mevcut model bilgisi
        current_model_info = self._get_enhanced_current_model_info()
        
        # Mevcut model bilgisi
        info_frame = tk.Frame(card, bg=self.colors['bg_secondary'])
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(info_frame, 
                text=f"Mevcut Model: {current_model_info['name']}",
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['text_primary'],
                bg=self.colors['bg_secondary']).pack(anchor=tk.W)
        
        tk.Label(info_frame,
                text=f"Durum: {current_model_info['status']}",
                font=("Segoe UI", 10),
                fg=self.colors['text_secondary'],
                bg=self.colors['bg_secondary']).pack(anchor=tk.W, pady=(5, 0))
        
        # Model seçimi
        tk.Label(card,
                text="Mevcut Modeller:",
                font=("Segoe UI", 12, "bold"),
                fg=self.colors['text_primary'],
                bg=self.colors['bg_secondary']).pack(anchor=tk.W, pady=(15, 5))
        
        # Model listesi
        model_frame = tk.Frame(card, bg=self.colors['bg_secondary'])
        model_frame.pack(fill=tk.X, pady=(0, 15))
        
        for model_name, model_data in self.available_models.items():
            self._create_model_option(model_frame, model_name, model_data)
        
        # Model işlemleri
        button_frame = tk.Frame(card, bg=self.colors['bg_secondary'])
        button_frame.pack(fill=tk.X)
        
        # DÜZELTME: Model değiştir butonu - app.py entegrasyonu
        change_btn = tk.Button(button_frame,
                              text="🔄 Modeli Değiştir",
                              font=("Segoe UI", 11, "bold"),
                              bg=self.colors['accent_primary'],
                              fg="#FFFFFF",
                              relief=tk.FLAT,
                              padx=15, pady=8,
                              command=self._change_model_enhanced,
                              cursor="hand2")
        change_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Model indir
        download_btn = tk.Button(button_frame,
                                text="📥 Model İndir",
                                font=("Segoe UI", 11, "bold"), 
                                bg=self.colors['accent_secondary'],
                                fg="#FFFFFF",
                                relief=tk.FLAT,
                                padx=15, pady=8,
                                command=self._download_model,
                                cursor="hand2")
        download_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Model yolu seç
        path_btn = tk.Button(button_frame,
                            text="📁 Model Dosyası Seç",
                            font=("Segoe UI", 11),
                            bg=self.colors['bg_tertiary'],
                            fg=self.colors['text_primary'],
                            relief=tk.FLAT,
                            padx=15, pady=8,
                            command=self._select_model_file,
                            cursor="hand2")
        path_btn.pack(side=tk.LEFT)

    def _get_enhanced_current_model_info(self):
        """DÜZELTME: Enhanced current model info."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'fall_detector'):
                fall_detector = self.app_instance.fall_detector
                if fall_detector and hasattr(fall_detector, 'get_enhanced_model_info'):
                    model_info = fall_detector.get_enhanced_model_info()
                    return {
                        'name': model_info.get('model_name', 'Bilinmiyor'),
                        'status': "🟢 Yüklü" if model_info.get('model_loaded') else "🔴 Yüklenmedi"
                    }
            
            # Fallback
            current_model = self._get_current_model_name()
            return {
                'name': current_model,
                'status': "🟡 Bilinmiyor"
            }
            
        except Exception as e:
            logging.error(f"❌ Enhanced model info alınamadı: {e}")
            return {
                'name': 'Hata',
                'status': "❌ Hata"
            }

    def _change_model_enhanced(self):
        """DÜZELTME: Enhanced AI model değiştirme - app.py entegrasyonu."""
        selected_model = self.selected_model_var.get()
        if not selected_model:
            messagebox.showwarning("Uyarı", "Lütfen bir model seçin.")
            return
        
        if not self.available_models[selected_model]['exists']:
            messagebox.showwarning("Uyarı", f"Seçili model ({selected_model}) henüz indirilmemiş.\nÖnce modeli indirin.")
            return
        
        # Onay iste
        model_data = self.available_models[selected_model]
        result = messagebox.askyesno(
            "AI Model Değiştir",
            f"AI modelini değiştirmek istiyor musunuz?\n\n"
            f"🤖 Yeni Model: {model_data['name']}\n"
            f"📊 Boyut: {model_data['size']}\n"
            f"⚡ Hız: {model_data['speed']}\n"
            f"🎯 Doğruluk: {model_data['accuracy']}\n\n"
            "⚠️ Bu işlem sistem performansını etkileyebilir."
        )
        
        if not result:
            return
        
        try:
            # DÜZELTME: app_instance üzerinden model değiştir
            if self.app_instance and hasattr(self.app_instance, 'switch_ai_model'):
                success = self.app_instance.switch_ai_model(selected_model)
                
                if success:
                    self._set_modified()
                    messagebox.showinfo(
                        "Model Değiştirildi! 🎉",
                        f"AI modeli başarıyla değiştirildi!\n\n"
                        f"🤖 Yeni Model: {model_data['name']}\n"
                        f"📊 Boyut: {model_data['size']}\n"
                        f"⚡ Hız: {model_data['speed']}\n"
                        f"🎯 Doğruluk: {model_data['accuracy']}\n\n"
                        "✅ Değişiklikler aktif!"
                    )
                    
                    # Model listesini yenile
                    self.available_models = self._scan_available_models()
                    logging.info(f"✅ Model başarıyla değiştirildi: {selected_model}")
                    
                else:
                    messagebox.showerror("Model Değiştirme Hatası", 
                                       "Model değiştirilemedi!\n\nOlası nedenler:\n"
                                       "• Model dosyası bozuk\n"
                                       "• Sistem kaynakları yetersiz\n"
                                       "• Model formatı uyumsuz")
                    
            else:
                # Fallback: Direct fall_detector kullan
                if self.fall_detector:
                    model_path = model_data['path']
                    # Basit model path güncellemesi
                    self.fall_detector.model_path = model_path
                    
                    messagebox.showinfo("Model Yolu Güncellendi", 
                                      f"Model yolu güncellendi: {selected_model}\n"
                                      "Sistemi yeniden başlatın.")
                    self._set_modified()
                else:
                    messagebox.showerror("Hata", "Model değiştirme sistemi bulunamadı!")
                
        except Exception as e:
            error_msg = f"Model değiştirme hatası: {str(e)}"
            logging.error(f"❌ {error_msg}")
            messagebox.showerror("Model Değiştirme Hatası", error_msg)

    def _create_model_option(self, parent, model_name, model_data):
        """Model seçeneği oluştur."""
        # Model container
        option_frame = tk.Frame(parent, bg=self.colors['bg_tertiary'], relief=tk.FLAT, bd=1)
        option_frame.pack(fill=tk.X, pady=2)
        
        # Radio button
        radio = tk.Radiobutton(option_frame,
                              text="",
                              variable=self.selected_model_var,
                              value=model_name,
                              bg=self.colors['bg_tertiary'],
                              command=lambda: self._set_modified())
        radio.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Model info
        info_frame = tk.Frame(option_frame, bg=self.colors['bg_tertiary'])
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=10)
        
        # Model adı ve durum
        name_frame = tk.Frame(info_frame, bg=self.colors['bg_tertiary'])
        name_frame.pack(fill=tk.X)
        
        model_label = tk.Label(name_frame,
                              text=model_data['name'],
                              font=("Segoe UI", 11, "bold"),
                              fg=self.colors['text_primary'],
                              bg=self.colors['bg_tertiary'])
        model_label.pack(side=tk.LEFT)
        
        # Durum badge
        if model_data['exists']:
            status_label = tk.Label(name_frame,
                                   text="✅ Mevcut",
                                   font=("Segoe UI", 9),
                                   fg=self.colors['accent_secondary'],
                                   bg=self.colors['bg_tertiary'])
        else:
            status_label = tk.Label(name_frame,
                                   text="⬇️ İndirilebilir",
                                   font=("Segoe UI", 9),
                                   fg=self.colors['accent_warning'],
                                   bg=self.colors['bg_tertiary'])
        status_label.pack(side=tk.RIGHT)
        
        # Model özellikleri
        props_text = f"Boyut: {model_data['size']} | Hız: {model_data['speed']} | Doğruluk: {model_data['accuracy']}"
        props_label = tk.Label(info_frame,
                              text=props_text,
                              font=("Segoe UI", 9),
                              fg=self.colors['text_secondary'],
                              bg=self.colors['bg_tertiary'])
        props_label.pack(anchor=tk.W)

    def _create_camera_settings_card(self, parent):
        """Kamera ayarları kartı."""
        card = self._create_card(parent, "📹 Kamera Ayarları")
        
        # Otomatik parlaklık
        auto_frame = tk.Frame(card, bg=self.colors['bg_secondary'])
        auto_frame.pack(fill=tk.X, pady=(0, 10))
        
        auto_check = tk.Checkbutton(auto_frame,
                                   text="Otomatik Parlaklık Ayarı",
                                   variable=self.auto_brightness_var,
                                   font=("Segoe UI", 11),
                                   fg=self.colors['text_primary'],
                                   bg=self.colors['bg_secondary'],
                                   command=self._toggle_auto_brightness)
        auto_check.pack(anchor=tk.W)
        
        # Manuel parlaklık
        brightness_frame = tk.Frame(card, bg=self.colors['bg_secondary'])
        brightness_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(brightness_frame,
                text="Parlaklık Ayarı (-100 ile +100):",
                font=("Segoe UI", 11),
                fg=self.colors['text_primary'],
                bg=self.colors['bg_secondary']).pack(anchor=tk.W)
        
        self.brightness_scale = tk.Scale(brightness_frame,
                                        from_=-100, to=100,
                                        orient=tk.HORIZONTAL,
                                        variable=self.brightness_var,
                                        bg=self.colors['bg_secondary'],
                                        fg=self.colors['text_primary'],
                                        command=self._apply_brightness)
        self.brightness_scale.pack(fill=tk.X, pady=(5, 0))
        
        # Kontrast
        contrast_frame = tk.Frame(card, bg=self.colors['bg_secondary'])
        contrast_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(contrast_frame,
                text="Kontrast (0.5 ile 2.0):",
                font=("Segoe UI", 11),
                fg=self.colors['text_primary'],
                bg=self.colors['bg_secondary']).pack(anchor=tk.W)
        
        self.contrast_scale = tk.Scale(contrast_frame,
                                      from_=0.5, to=2.0,
                                      resolution=0.1,
                                      orient=tk.HORIZONTAL,
                                      variable=self.contrast_var,
                                      bg=self.colors['bg_secondary'],
                                      fg=self.colors['text_primary'],
                                      command=self._apply_contrast)
        self.contrast_scale.pack(fill=tk.X, pady=(5, 0))
        
        # Kamera test
        test_btn = tk.Button(card,
                            text="🎥 Kamera Ayarlarını Test Et",
                            font=("Segoe UI", 11),
                            bg=self.colors['accent_primary'],
                            fg="#FFFFFF",
                            relief=tk.FLAT,
                            padx=15, pady=8,
                            command=self._test_camera_settings,
                            cursor="hand2")
        test_btn.pack(pady=(10, 0))

    def _create_notification_card(self, parent):
        """DÜZELTME: Bildirim ayarları kartı - Test bildirimi özelliği eklendi."""
        card = self._create_card(parent, "🔔 Bildirim Ayarları")
        
        # E-posta bildirimi
        email_check = tk.Checkbutton(card,
                                    text=f"E-posta Bildirimleri ({self.user.get('email', '')})",
                                    variable=self.email_notification_var,
                                    font=("Segoe UI", 11),
                                    fg=self.colors['text_primary'],
                                    bg=self.colors['bg_secondary'],
                                    command=lambda: self._set_modified())
        email_check.pack(anchor=tk.W, pady=5)
        
        # FCM (Push) bildirimi
        fcm_check = tk.Checkbutton(card,
                                  text="Mobil Push Bildirimleri",
                                  variable=self.fcm_notification_var,
                                  font=("Segoe UI", 11),
                                  fg=self.colors['text_primary'],
                                  bg=self.colors['bg_secondary'],
                                  command=lambda: self._set_modified())
        fcm_check.pack(anchor=tk.W, pady=5)
        
        # SMS bildirimi
        sms_check = tk.Checkbutton(card,
                                  text="SMS Bildirimleri",
                                  variable=self.sms_notification_var,
                                  font=("Segoe UI", 11),
                                  fg=self.colors['text_primary'],
                                  bg=self.colors['bg_secondary'],
                                  command=self._toggle_sms)
        sms_check.pack(anchor=tk.W, pady=5)
        
        # Telefon numarası
        phone_frame = tk.Frame(card, bg=self.colors['bg_secondary'])
        phone_frame.pack(fill=tk.X, padx=(20, 0), pady=5)
        
        tk.Label(phone_frame,
                text="Telefon Numarası:",
                font=("Segoe UI", 10),
                fg=self.colors['text_secondary'],
                bg=self.colors['bg_secondary']).pack(anchor=tk.W)
        
        self.phone_entry = tk.Entry(phone_frame,
                                   textvariable=self.phone_var,
                                   font=("Segoe UI", 11),
                                   state="disabled" if not self.sms_notification_var.get() else "normal")
        self.phone_entry.pack(fill=tk.X, pady=(5, 0))
        
        # DÜZELTME: Test bildirimi - Enhanced versiyon
        test_frame = tk.Frame(card, bg=self.colors['bg_secondary'])
        test_frame.pack(fill=tk.X, pady=(15, 0))
        
        # Test butonları yan yana
        instant_test_btn = tk.Button(test_frame,
                                    text="⚡ Anında Test",
                                    font=("Segoe UI", 11, "bold"),
                                    bg=self.colors['accent_warning'],
                                    fg="#FFFFFF",
                                    relief=tk.FLAT,
                                    padx=15, pady=8,
                                    command=self._send_instant_test_notification_enhanced,
                                    cursor="hand2")
        instant_test_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        full_test_btn = tk.Button(test_frame,
                                 text="📧 Tam Test",
                                 font=("Segoe UI", 11),
                                 bg=self.colors['accent_secondary'],
                                 fg="#FFFFFF",
                                 relief=tk.FLAT,
                                 padx=15, pady=8,
                                 command=self._test_notifications_enhanced,
                                 cursor="hand2")
        full_test_btn.pack(side=tk.LEFT)

    def _create_fall_detection_card(self, parent):
        """Düşme algılama ayarları kartı."""
        card = self._create_card(parent, "🚨 Düşme Algılama Ayarları")
        
        # Hassasiyet seviyesi
        tk.Label(card,
                text="Algılama Hassasiyeti:",
                font=("Segoe UI", 12, "bold"),
                fg=self.colors['text_primary'],
                bg=self.colors['bg_secondary']).pack(anchor=tk.W, pady=(0, 10))
        
        sensitivity_levels = [
            ("low", "Düşük - Az uyarı, yüksek doğruluk"),
            ("medium", "Orta - Dengeli (Önerilen)"),
            ("high", "Yüksek - Daha fazla uyarı"),
            ("ultra", "Ultra - Maksimum hassasiyet")
        ]
        
        for value, description in sensitivity_levels:
            radio = tk.Radiobutton(card,
                                  text=description,
                                  variable=self.sensitivity_var,
                                  value=value,
                                  font=("Segoe UI", 10),
                                  fg=self.colors['text_primary'],
                                  bg=self.colors['bg_secondary'],
                                  command=lambda: self._set_modified())
            radio.pack(anchor=tk.W, pady=2)

    def _create_appearance_card(self, parent):
        """Görünüm ayarları kartı."""
        card = self._create_card(parent, "🎨 Görünüm ve Tema")
        
        # Koyu mod
        dark_check = tk.Checkbutton(card,
                                   text="Koyu Mod",
                                   variable=self.dark_mode_var,
                                   font=("Segoe UI", 11),
                                   fg=self.colors['text_primary'],
                                   bg=self.colors['bg_secondary'],
                                   command=self._preview_theme)
        dark_check.pack(anchor=tk.W, pady=10)
        
        # Tema önizleme
        preview_btn = tk.Button(card,
                               text="👁️ Temayı Önizle",
                               font=("Segoe UI", 11),
                               bg=self.colors['accent_primary'],
                               fg="#FFFFFF",
                               relief=tk.FLAT,
                               padx=15, pady=8,
                               command=self._preview_theme,
                               cursor="hand2")
        preview_btn.pack(pady=(0, 10))

    def _create_card(self, parent, title):
        """Kart container oluştur."""
        # Ana kart
        card_container = tk.Frame(parent, bg=self.colors['bg_primary'])
        card_container.pack(fill=tk.X, padx=20, pady=10)
        
        # Başlık
        title_frame = tk.Frame(card_container, bg=self.colors['bg_secondary'], height=40)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame,
                              text=title,
                              font=("Segoe UI", 14, "bold"),
                              fg=self.colors['text_primary'],
                              bg=self.colors['bg_secondary'])
        title_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        # İçerik
        content_frame = tk.Frame(card_container, bg=self.colors['bg_secondary'], relief=tk.FLAT, bd=1)
        content_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        
        # Padding
        padded_frame = tk.Frame(content_frame, bg=self.colors['bg_secondary'])
        padded_frame.pack(fill=tk.X, padx=15, pady=15)
        
        return padded_frame

    def _create_input_field(self, parent, label_text, variable, readonly=False):
        """Input alanı oluştur."""
        # Label
        tk.Label(parent,
                text=label_text,
                font=("Segoe UI", 11),
                fg=self.colors['text_primary'],
                bg=self.colors['bg_secondary']).pack(anchor=tk.W, pady=(0, 5))
        
        # Entry
        entry = tk.Entry(parent,
                        textvariable=variable,
                        font=("Segoe UI", 11),
                        state="readonly" if readonly else "normal")
        entry.pack(fill=tk.X, pady=(0, 15))
        
        if not readonly:
            entry.bind('<KeyRelease>', lambda e: self._set_modified())
        
        return entry

    def _download_model(self):
        """Model indir."""
        selected_model = self.selected_model_var.get()
        if not selected_model:
            messagebox.showwarning("Uyarı", "Lütfen indirmek istediğiniz modeli seçin.")
            return
        
        if self.available_models[selected_model]['exists']:
            messagebox.showinfo("Bilgi", f"Model '{selected_model}' zaten mevcut.")
            return
        
        # İndirme onayı
        model_info = self.available_models[selected_model]
        result = messagebox.askyesno(
            "Model İndir",
            f"Modeli indirmek istiyor musunuz?\n\n"
            f"Model: {model_info['name']}\n"
            f"Tahmini Boyut: {model_info['size']}\n\n"
            "İndirme işlemi internet bağlantısına göre zaman alabilir."
        )
        
        if not result:
            return
        
        # İndirme işlemini başlat
        self._start_model_download(selected_model)

    def _start_model_download(self, model_name):
        """Model indirme işlemini başlat."""
        def download_worker():
            try:
                # Progress dialog oluştur
                self._show_download_progress(model_name)
                
                # YOLO model indirme
                from ultralytics import YOLO
                
                # Model indir
                model_path = os.path.join(self.model_directory, f"{model_name}.pt")
                model = YOLO(f"{model_name}.pt")  # Bu otomatik indirir
                
                # İndirilen modeli hedef dizine taşı
                import shutil
                default_path = os.path.join(os.path.expanduser("~"), ".ultralytics", "models", f"{model_name}.pt")
                
                if os.path.exists(default_path):
                    shutil.copy2(default_path, model_path)
                    logging.info(f"Model başarıyla indirildi: {model_path}")
                    
                    # UI'yı güncelle
                    self.after(0, lambda: self._on_download_complete(model_name, True))
                else:
                    self.after(0, lambda: self._on_download_complete(model_name, False, "Model dosyası bulunamadı"))
                
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Model indirme hatası: {error_msg}")
                self.after(0, lambda: self._on_download_complete(model_name, False, error_msg))
        
        # Thread'de indir
        download_thread = threading.Thread(target=download_worker, daemon=True)
        download_thread.start()

    def _show_download_progress(self, model_name):
        """İndirme progress dialog göster."""
        self.progress_window = tk.Toplevel(self)
        self.progress_window.title("Model İndiriliyor")
        self.progress_window.geometry("400x150")
        self.progress_window.resizable(False, False)
        self.progress_window.transient(self)
        self.progress_window.grab_set()
        
        # Center window
        self.progress_window.update_idletasks()
        x = (self.progress_window.winfo_screenwidth() - 400) // 2
        y = (self.progress_window.winfo_screenheight() - 150) // 2
        self.progress_window.geometry(f"400x150+{x}+{y}")
        
        # Content
        tk.Label(self.progress_window,
                text=f"Model indiriliyor: {model_name}",
                font=("Segoe UI", 12, "bold")).pack(pady=20)
        
        # Progress bar
        from tkinter import ttk
        progress = ttk.Progressbar(self.progress_window, mode='indeterminate')
        progress.pack(pady=10, padx=50, fill=tk.X)
        progress.start()
        
        tk.Label(self.progress_window,
                text="Lütfen bekleyin...",
                font=("Segoe UI", 10)).pack(pady=10)

    def _on_download_complete(self, model_name, success, error_msg=None):
        """İndirme tamamlandığında."""
        try:
            self.progress_window.destroy()
        except:
            pass
        
        if success:
            messagebox.showinfo("Başarı", f"Model '{model_name}' başarıyla indirildi!")
            # Model listesini yenile
            self.available_models = self._scan_available_models()
            self._refresh_ui()
        else:
            messagebox.showerror("Hata", f"Model indirilemedi:\n{error_msg}")

    def _select_model_file(self):
        """Model dosyası seç."""
        file_path = filedialog.askopenfilename(
            title="Model Dosyası Seçin",
            filetypes=[("PyTorch Models", "*.pt"), ("All Files", "*.*")],
            initialdir=self.model_directory
        )
        
        if file_path:
            try:
                # Dosyayı model dizinine kopyala
                import shutil
                model_name = os.path.basename(file_path).replace('.pt', '')
                target_path = os.path.join(self.model_directory, f"{model_name}.pt")
                
                shutil.copy2(file_path, target_path)
                
                messagebox.showinfo("Başarı", f"Model dosyası başarıyla eklendi: {model_name}")
                
                # Model listesini yenile
                self.available_models = self._scan_available_models()
                self._refresh_ui()
                
            except Exception as e:
                messagebox.showerror("Hata", f"Model dosyası kopyalanamadı:\n{str(e)}")

    def _toggle_auto_brightness(self):
        """Otomatik parlaklık toggle."""
        auto_enabled = self.auto_brightness_var.get()
        
        # Scale'leri enable/disable et
        state = "disabled" if auto_enabled else "normal"
        self.brightness_scale.config(state=state)
        self.contrast_scale.config(state=state)
        
        # Kameralara uygula
        self._apply_camera_settings()
        self._set_modified()

    def _apply_brightness(self, value=None):
        """Parlaklık ayarını uygula."""
        if not self.auto_brightness_var.get():
            self._apply_camera_settings()
        self._set_modified()

    def _apply_contrast(self, value=None):
        """Kontrast ayarını uygula."""
        if not self.auto_brightness_var.get():
            self._apply_camera_settings()
        self._set_modified()

    def _apply_camera_settings(self):
        """Kamera ayarlarını uygula."""
        try:
            auto_brightness = self.auto_brightness_var.get()
            brightness = self.brightness_var.get()
            contrast = self.contrast_var.get()
            
            # Tüm kameralara uygula
            for camera in self.cameras:
                if hasattr(camera, 'enable_auto_brightness'):
                    camera.enable_auto_brightness(auto_brightness)
                if hasattr(camera, 'set_brightness') and not auto_brightness:
                    camera.set_brightness(brightness)
                if hasattr(camera, 'set_contrast'):
                    camera.set_contrast(contrast)
            
            logging.info(f"Kamera ayarları uygulandı: auto={auto_brightness}, brightness={brightness}, contrast={contrast}")
            
        except Exception as e:
            logging.error(f"Kamera ayarları uygulama hatası: {e}")

    def _test_camera_settings(self):
        """Kamera ayarlarını test et."""
        try:
            self._apply_camera_settings()
            
            # Test sonucu
            active_cameras = len([cam for cam in self.cameras if hasattr(cam, 'is_running') and cam.is_running])
            
            messagebox.showinfo(
                "Kamera Test Sonucu",
                f"Kamera ayarları başarıyla uygulandı!\n\n"
                f"Aktif Kameralar: {active_cameras}/{len(self.cameras)}\n"
                f"Otomatik Parlaklık: {'Açık' if self.auto_brightness_var.get() else 'Kapalı'}\n"
                f"Parlaklık: {self.brightness_var.get()}\n"
                f"Kontrast: {self.contrast_var.get():.1f}"
            )
            
        except Exception as e:
            messagebox.showerror("Test Hatası", f"Kamera ayarları test edilemedi:\n{str(e)}")

    def _toggle_sms(self):
        """SMS toggle."""
        sms_enabled = self.sms_notification_var.get()
        self.phone_entry.config(state="normal" if sms_enabled else "disabled")
        self._set_modified()

    def _send_instant_test_notification_enhanced(self):
        """
        DÜZELTME: Enhanced anında test bildirimi - app.py entegrasyonu ile
        """
        try:
            logging.info("⚡ Enhanced anında test bildirimi gönderiliyor...")
            
            # DÜZELTME: app_instance üzerinden NotificationManager al
            notification_manager = self._get_notification_manager_enhanced()
            if not notification_manager:
                messagebox.showerror("Hata", "Bildirim sistemi bulunamadı!\n\nApp instance veya NotificationManager başlatılmamış.")
                return
            
            # Test olayı verisi oluştur
            test_event_data = {
                "id": str(uuid.uuid4()),
                "user_id": self.user["localId"],
                "timestamp": time.time(),
                "confidence": 0.95,  # %95 güvenilirlik
                "image_url": None,  # Test için resim yok
                "detection_method": "ENHANCED_TEST_NOTIFICATION",
                "camera_id": "settings_test_camera",
                "track_id": 999,
                "test": True,  # Bu bir test bildirimi
                "enhanced_summary": "Enhanced Settings Test - Anında gönderim sistemi",
                "severity_level": "medium"
            }
            
            # Test screenshot oluştur
            test_screenshot = self._create_test_screenshot_enhanced()
            
            # DÜZELTME: Kullanıcı ayarlarını notification manager'a aktar
            current_user_data = {
                "localId": self.user["localId"],
                "email": self.user.get("email", ""),
                "email_notification": self.email_notification_var.get(),
                "fcm_notification": self.fcm_notification_var.get(),
                "sms_notification": self.sms_notification_var.get(),
                "phone_number": self.phone_var.get().strip(),
                "fcmToken": self.user_data.get("fcmToken"),  # FCM token'ı
                "settings": {
                    "email_notification": self.email_notification_var.get(),
                    "fcm_notification": self.fcm_notification_var.get(),
                    "sms_notification": self.sms_notification_var.get(),
                    "phone_number": self.phone_var.get().strip()
                }
            }
            
            # NotificationManager'ı güncelle
            notification_manager.update_user_data(current_user_data)
            
            # Bildirimi gönder
            success = notification_manager.send_notifications(test_event_data, test_screenshot)
            
            if success:
                # Aktif kanalları belirle
                active_channels = []
                if self.email_notification_var.get():
                    active_channels.append("📧 E-posta")
                if self.fcm_notification_var.get():
                    active_channels.append("📱 Push Bildirimi")
                if self.sms_notification_var.get() and self.phone_var.get().strip():
                    active_channels.append("📲 SMS")
                
                messagebox.showinfo(
                    "Enhanced Test Bildirimi Başarılı! ⚡",
                    f"Enhanced anında test bildirimi gönderildi!\n\n"
                    f"🎯 Aktif Kanallar ({len(active_channels)}):\n"
                    f"{'• ' + chr(10) + '• '.join(active_channels) if active_channels else '• Varsayılan kanal'}\n\n"
                    f"⏰ Gönderim Zamanı: {datetime.now().strftime('%H:%M:%S')}\n"
                    f"🆔 Test ID: {test_event_data['id'][:8]}...\n"
                    f"🔧 Sistem: Enhanced Settings Panel\n\n"
                    "📬 Bildirimlerinizi kontrol edin!"
                )
                
                logging.info(f"✅ Enhanced anında test bildirimi başarılı: {active_channels}")
                
            else:
                messagebox.showerror(
                    "Enhanced Test Bildirimi Başarısız!",
                    "Enhanced test bildirimi gönderilemedi!\n\n"
                    "Olası nedenler:\n"
                    "• Internet bağlantısı problemi\n"
                    "• Bildirim ayarları eksik\n"
                    "• SMTP/SMS servisleri yapılandırılmamış\n"
                    "• FCM token eksik\n\n"
                    "Lütfen ayarlarınızı kontrol edin."
                )
                logging.error("❌ Enhanced anında test bildirimi başarısız")
            
        except Exception as e:
            error_msg = f"Enhanced anında test bildirimi hatası: {str(e)}"
            logging.error(f"❌ {error_msg}")
            messagebox.showerror("Enhanced Test Hatası", error_msg)

    def _create_test_screenshot_enhanced(self):
        """DÜZELTME: Enhanced test için renkli screenshot oluştur."""
        try:
            # 640x480 renkli test görüntüsü
            test_image = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Enhanced renkli desenler
            test_image[0:120, :] = [255, 100, 100]    # Kırmızı
            test_image[120:240, :] = [100, 255, 100]  # Yeşil  
            test_image[240:360, :] = [100, 100, 255]  # Mavi
            test_image[360:480, :] = [255, 255, 100]  # Sarı
            
            # Test metni ekle (OpenCV gerekli)
            try:
                import cv2
                cv2.putText(test_image, "ENHANCED SETTINGS TEST", (120, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(test_image, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                           (160, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(test_image, "Guard AI Enhanced Notification", 
                           (110, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(test_image, "Settings Panel Integration", 
                           (140, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            except ImportError:
                pass  # OpenCV yoksa sadece renkli bloklar
            
            return test_image
            
        except Exception as e:
            logging.error(f"Enhanced test screenshot oluşturma hatası: {e}")
            # Basit siyah görüntü döndür
            return np.zeros((480, 640, 3), dtype=np.uint8)

    def _get_notification_manager_enhanced(self):
        """DÜZELTME: Enhanced NotificationManager instance'ını al."""
        try:
            # DÜZELTME: Önce app_instance'dan dene
            if self.app_instance and hasattr(self.app_instance, 'notification_manager'):
                return self.app_instance.notification_manager
            
            # Widget hiyerarşisinde yukarı çıkarak ana uygulamayı bul
            widget = self.master
            while widget:
                if hasattr(widget, 'notification_manager'):
                    return widget.notification_manager
                widget = widget.master
            
            # Direkt NotificationManager sınıfını import edip instance al
            from core.notification import NotificationManager
            return NotificationManager.get_instance(self.user_data)
            
        except Exception as e:
            logging.error(f"❌ Enhanced NotificationManager alınamadı: {e}")
            return None

    def _test_notifications_enhanced(self):
        """DÜZELTME: Enhanced bildirimleri test et."""
        try:
            active_notifications = []
            
            if self.email_notification_var.get():
                active_notifications.append("📧 E-posta")
            if self.fcm_notification_var.get():
                active_notifications.append("📱 Push Bildirimi")
            if self.sms_notification_var.get() and self.phone_var.get().strip():
                active_notifications.append("📲 SMS")
            
            if not active_notifications:
                messagebox.showwarning("Uyarı", "Hiçbir bildirim türü aktif değil.\n\nLütfen en az bir bildirim türünü etkinleştirin.")
                return
            
            # Test bildirimi onayı
            test_result = messagebox.askyesno(
                "Enhanced Tam Bildirim Testi",
                f"Aşağıdaki bildirim türleri test edilecek:\n\n"
                f"{'• ' + chr(10) + '• '.join(active_notifications)}\n\n"
                "Bu enhanced tam bir test olup gerçek bildirim sistemini kullanır.\n"
                "Enhanced test bildirimi göndermek istiyor musunuz?"
            )
            
            if test_result:
                # Enhanced anında test bildirimi fonksiyonunu çağır
                self._send_instant_test_notification_enhanced()
            
        except Exception as e:
            messagebox.showerror("Enhanced Test Hatası", f"Enhanced bildirim testi yapılamadı:\n{str(e)}")

    def _preview_theme(self):
        """Tema önizleme."""
        self.dark_mode = self.dark_mode_var.get()
        self._setup_colors()
        self._setup_styles()
        self._refresh_ui()
        self._set_modified()

    def _refresh_ui(self):
        """UI'yi yenile."""
        try:
            # Mevcut mouse wheel binding'ini temizle
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.unbind_all("<MouseWheel>")
            
            # Mevcut widget'ları temizle
            for widget in self.winfo_children():
                widget.destroy()
            
            # UI'yi yeniden oluştur
            self._create_enhanced_ui()
            
        except Exception as e:
            logging.error(f"UI refresh hatası: {e}")

    def _set_modified(self):
        """Değişiklik işaretle."""
        self.is_modified = True

    def _save_settings(self):
        """DÜZELTME: Enhanced ayarları kaydet - app.py entegrasyonu ile."""
        try:
            # Yeni ayarları hazırla
            settings = {
                "email_notification": self.email_notification_var.get(),
                "fcm_notification": self.fcm_notification_var.get(),
                "sms_notification": self.sms_notification_var.get(),
                "phone_number": self.phone_var.get().strip(),
                "dark_mode": self.dark_mode_var.get(),
                "auto_brightness": self.auto_brightness_var.get(),
                "brightness_adjustment": self.brightness_var.get(),
                "contrast_adjustment": self.contrast_var.get(),
                "fall_sensitivity": self.sensitivity_var.get(),
                "selected_ai_model": self.selected_model_var.get()
            }
            
            # Kullanıcı bilgileri
            user_data = {
                "displayName": self.name_var.get().strip()
            }
            
            logging.info(f"✅ Enhanced ayarlar kaydediliyor - User: {self.user['localId']}")
            logging.info(f"📊 Settings: {settings}")
            logging.info(f"👤 User data: {user_data}")
            
            # Veritabanında güncelle
            user_update_success = self.db_manager.update_user_data(self.user["localId"], user_data)
            settings_update_success = self.db_manager.save_user_settings(self.user["localId"], settings)
            
            if user_update_success and settings_update_success:
                # Kullanıcı nesnesini güncelle
                self.user["displayName"] = user_data["displayName"]
                
                # Kamera ayarlarını uygula
                self._apply_camera_settings()
                
                # DÜZELTME: Ana uygulamaya ayarları aktar (AI model değişikliği için)
                if self.app_instance:
                    # App instance'a ayarları aktar
                    if hasattr(self.app_instance, 'update_user_settings'):
                        self.app_instance.update_user_settings(settings)
                    
                    # Notification manager'ı güncelle
                    if hasattr(self.app_instance, 'notification_manager') and self.app_instance.notification_manager:
                        updated_user_data = self.user_data.copy() if self.user_data else {}
                        updated_user_data.update({
                            "settings": settings,
                            "email_notification": settings["email_notification"],
                            "fcm_notification": settings["fcm_notification"],
                            "sms_notification": settings["sms_notification"],
                            "phone_number": settings["phone_number"]
                        })
                        self.app_instance.notification_manager.update_user_data(updated_user_data)
                
                self.is_modified = False
                
                messagebox.showinfo(
                    "Enhanced Ayarlar Kaydedildi! 🎉",
                    "Tüm enhanced ayarlarınız başarıyla kaydedildi!\n\n"
                    "✅ Kullanıcı bilgileri güncellendi\n"
                    "✅ Bildirim tercihleri kaydedildi\n"
                    "✅ Kamera ayarları uygulandı\n"
                    "✅ AI model ayarları güncellendi\n"
                    "✅ Tema ayarları aktifleştirildi\n\n"
                    "🚀 Enhanced değişiklikler aktif oturum için uygulandı!"
                )
                
                self._on_back()
            else:
                messagebox.showerror(
                    "Enhanced Kaydetme Hatası",
                    "Enhanced ayarlar kaydedilirken bir hata oluştu.\n"
                    "Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin.\n\n"
                    f"Kullanıcı güncelleme: {'✅' if user_update_success else '❌'}\n"
                    f"Enhanced ayarlar güncelleme: {'✅' if settings_update_success else '❌'}"
                )
            
        except Exception as e:
            logging.error(f"❌ Enhanced ayarlar kaydetme hatası: {e}")
            messagebox.showerror(
                "Enhanced Kaydetme Hatası",
                f"Enhanced ayarlar kaydedilirken hata oluştu:\n{str(e)}\n\n"
                "Enhanced ayarlar yerel depolamaya kaydedilmeye çalışılacak."
            )

    def _on_back(self):
        """Geri dönüş."""
        if self.is_modified:
            result = messagebox.askyesnocancel(
                "Enhanced Değişiklikler Kaydedilmedi",
                "Enhanced değişiklikleriniz kaydedilmedi.\n\n"
                "Enhanced ayarları kaydetmek istiyor musunuz?"
            )
            
            if result is True:  # Evet - Kaydet
                self._save_settings()
                return
            elif result is None:  # İptal
                return
            # Hayır - Kaydetme, devam et
        
        try:
            # Widget temizliği
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.unbind_all("<MouseWheel>")
        except:
            pass
        
        self.back_fn()


# DÜZELTME: Backward compatibility - SettingsFrame alias
SettingsFrame = EnhancedSettingsFrame


if __name__ == "__main__":
    # Enhanced Test
    root = tk.Tk()
    root.title("Enhanced Settings Test - v3.0")
    root.geometry("1400x900")
    
    # Mock data
    user = {"localId": "enhanced_test", "displayName": "Enhanced Test User", "email": "enhanced@test.com"}
    
    class MockDBManager:
        def get_user_data(self, user_id): 
            return {
                "settings": {
                    "email_notification": True,
                    "fcm_notification": True,
                    "sms_notification": False,
                    "phone_number": "",
                    "dark_mode": False,
                    "auto_brightness": True,
                    "brightness_adjustment": 0,
                    "contrast_adjustment": 1.0,
                    "fall_sensitivity": "medium",
                    "selected_ai_model": "yolo11l-pose"
                },
                "fcmToken": "mock_fcm_token"
            }
        def update_user_data(self, user_id, data): 
            print(f"✅ MockDB: Enhanced user data updated for {user_id}: {data}")
            return True
        def save_user_settings(self, user_id, settings): 
            print(f"✅ MockDB: Enhanced settings saved for {user_id}: {settings}")
            return True
    
    class MockFallDetector:
        def __init__(self):
            self.model_path = "/path/to/yolo11l-pose.pt"
        
        def get_enhanced_model_info(self):
            return {
                "model_name": "yolo11l-pose",
                "model_loaded": True,
                "device": "CPU",
                "keypoints_count": 17
            }
    
    class MockApp:
        def __init__(self):
            self.cameras = []
            self.fall_detector = MockFallDetector()
            self.notification_manager = None
            self.system_state = {
                'current_model': 'yolo11l-pose'
            }
        
        def switch_ai_model(self, model_name):
            print(f"🔄 MockApp: Enhanced AI model switch to {model_name}")
            return True
        
        def update_user_settings(self, settings):
            print(f"⚙️ MockApp: Enhanced user settings updated: {settings}")
    
    def enhanced_test_back():
        print("✅ Enhanced back button pressed")
        root.quit()
    
    # DÜZELTME: app_instance parametresi ile test
    mock_app = MockApp()
    settings = EnhancedSettingsFrame(
        root, user, MockDBManager(), 
        enhanced_test_back, MockFallDetector(), mock_app
    )
    settings.pack(fill=tk.BOTH, expand=True)
    
    print("🧪 Enhanced Settings Test v3.0 Başlatıldı")
    print("✨ ENHANCED YENİ ÖZELLİKLER:")
    print("   ⚡ Enhanced Anında Test Bildirimi")
    print("   📧 Enhanced Tam Bildirim Testi") 
    print("   🎨 Enhanced UI/UX")
    print("   🔧 Enhanced Model Yönetimi (app.py entegrasyonu)")
    print("   📱 Enhanced Mobil Push Desteği")
    print("   🔗 Enhanced App Instance Entegrasyonu")
    
    root.mainloop()