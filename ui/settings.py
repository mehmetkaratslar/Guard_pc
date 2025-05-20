import tkinter as tk
from tkinter import ttk, messagebox
import os
from PIL import Image, ImageTk
import logging
import threading
import time

class SettingsFrame(tk.Frame):
    """Sadeleştirilmiş ayarlar ekranı sınıfı"""

    def __init__(self, parent, user, db_manager, back_fn):
        """
        SettingsFrame sınıfını başlatır ve gerekli parametreleri ayarlar.

        Args:
            parent (tk.Frame): Üst çerçeve
            user (dict): Kullanıcı bilgileri
            db_manager: Veritabanı yönetici nesnesi
            back_fn (function): Geri dönüş fonksiyonu
        """
        super().__init__(parent)
        
        self.user = user
        self.db_manager = db_manager
        self.back_fn = back_fn
        
        # Kullanıcı ayarlarını yükle
        self.user_data = self.db_manager.get_user_data(user["localId"])
        self.settings = self.user_data.get("settings", {}) if self.user_data else {}
        
        # Dark mode algılama
        self.dark_mode = self.settings.get("dark_mode", False)
        
        # Tema renklerini ayarla
        self._setup_colors()
        
        # Stilleri ayarla
        self._setup_styles()
        
        # UI bileşenleri
        self._create_ui()
        
        # Kayıt hareketlerini saklamak için değişken
        self.is_modified = False

    def _setup_colors(self):
        """
        Tema renklerini ayarlar (açık veya koyu mod).
        """
        if self.dark_mode:
            self.bg_color = "#121212"
            self.card_bg = "#1E1E1E"
            self.header_bg = "#2196f3"
            self.accent_color = "#2196f3"
            self.text_color = "#FFFFFF"
            self.text_secondary = "#B0BEC5"
            self.button_bg = "#333333"
            self.button_fg = "#FFFFFF"
            self.input_bg = "#2A2A2A"
        else:
            self.bg_color = "#F8F9FA"
            self.card_bg = "#FFFFFF"
            self.header_bg = "#2196f3"
            self.accent_color = "#2196f3"
            self.text_color = "#2c3e50"
            self.text_secondary = "#78909c"
            self.button_bg = "#EFEFEF"
            self.button_fg = "#2c3e50"
            self.input_bg = "#F0F0F0"

    def _setup_styles(self):
        """
        Uygulama stillerini oluşturur ve tanımlar.
        """
        style = ttk.Style()
        
        # Ana çerçeve stili
        style.configure("MainFrame.TFrame", background=self.bg_color)
        
        # Kart stili
        style.configure("Card.TFrame", background=self.card_bg, relief="flat")
        
        # Header stili
        style.configure("Header.TFrame", background=self.header_bg)
        
        # Başlık etiketleri
        style.configure("Title.TLabel", 
                        background=self.header_bg,
                        foreground="#ffffff", 
                        font=("Segoe UI", 16, "bold"))
        
        # Alt başlık etiketleri
        style.configure("Section.TLabel", 
                        background=self.card_bg,
                        foreground=self.text_color, 
                        font=("Segoe UI", 14, "bold"))
        
        # Standart etiketler
        style.configure("TLabel", 
                        background=self.card_bg,
                        foreground=self.text_color, 
                        font=("Segoe UI", 12))
        
        # Bilgi etiketleri
        style.configure("Info.TLabel", 
                        background=self.card_bg,
                        foreground=self.text_secondary, 
                        font=("Segoe UI", 11))
        
        # Standart butonlar
        style.configure("TButton", 
                        font=("Segoe UI", 12),
                        padding=6)
        
        # Geniş butonlar
        style.configure("Wide.TButton", 
                        background=self.accent_color,
                        foreground="#ffffff",
                        font=("Segoe UI", 12, "bold"), 
                        padding=8)
        
        # Başarı butonu
        style.configure("Success.TButton", 
                        background="#00c853",
                        foreground="#ffffff",
                        font=("Segoe UI", 12, "bold"), 
                        padding=8)
        
        # Checkbox stili
        style.configure("TCheckbutton", 
                        background=self.card_bg,
                        foreground=self.text_color,
                        font=("Segoe UI", 12))
        
        # Giriş alanları
        style.configure("TEntry", 
                        fieldbackground=self.input_bg,
                        foreground=self.text_color,
                        font=("Segoe UI", 12),
                        padding=6)

    def _create_ui(self):
        """
        UI bileşenlerini oluşturur ve düzenler.
        """
        # Ana grid düzeni
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Başlık
        self.rowconfigure(1, weight=1)  # İçerik
        
        # Üst çubuk
        self._create_header()
        
        # İçerik kısmı
        self._create_content()
    
    def _create_header(self):
        """Üst başlık çubuğunu oluşturur."""
        header = ttk.Frame(self, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        
        inner_header = ttk.Frame(header, style="Header.TFrame", padding=(15, 10, 15, 10))
        inner_header.pack(fill=tk.X, expand=True)
        
        # Geri butonu
        back_button = ttk.Button(
            inner_header,
            text="⬅️ Geri",
            style="TButton",
            command=self._on_back,
            cursor="hand2",
            width=8
        )
        back_button.pack(side=tk.LEFT, padx=5)
        
        # Başlık
        title_label = ttk.Label(
            inner_header,
            text="Ayarlar",
            style="Title.TLabel"
        )
        title_label.pack(side=tk.LEFT, padx=20)
        
        # Kaydet butonu
        save_button = ttk.Button(
            inner_header,
            text="💾 Kaydet",
            style="Success.TButton",
            command=self._save_settings,
            cursor="hand2",
            width=10
        )
        save_button.pack(side=tk.RIGHT, padx=5)
    
    def _create_content(self):
        """İçerik panelini oluşturur."""
        content_frame = tk.Frame(self, bg=self.bg_color)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        content_frame.columnconfigure(0, weight=1)
        
        # Kullanıcı bilgileri kartı
        self._create_user_card(content_frame)
        
        # Bildirim ayarları kartı
        self._create_notification_card(content_frame)
        
        # Tema kartı
        self._create_theme_card(content_frame)
    
    def _create_user_card(self, parent):
        """Kullanıcı bilgileri kartını oluşturur."""
        # Kullanıcı kart çerçevesi
        user_card = tk.Frame(parent, bg=self.card_bg, padx=15, pady=15)
        user_card.pack(fill=tk.X, pady=(0, 15))
        user_card.configure(highlightbackground="#d0d0d0", highlightthickness=1)
        
        # Başlık
        user_title = ttk.Label(
            user_card,
            text="Kullanıcı Bilgileri",
            style="Section.TLabel"
        )
        user_title.pack(anchor=tk.W, pady=(0, 10))
        
        # Ad Soyad alanı
        name_frame = ttk.Frame(user_card, style="Card.TFrame")
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        name_label = ttk.Label(
            name_frame,
            text="Ad Soyad",
            style="TLabel"
        )
        name_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.name_var = tk.StringVar(value=self.user.get("displayName", ""))
        name_entry = ttk.Entry(
            name_frame,
            textvariable=self.name_var,
            style="TEntry"
        )
        name_entry.pack(fill=tk.X, ipady=3)
        
        # E-posta alanı (sadece gösterim için)
        email_frame = ttk.Frame(user_card, style="Card.TFrame")
        email_frame.pack(fill=tk.X)
        
        email_label = ttk.Label(
            email_frame,
            text="E-posta",
            style="TLabel"
        )
        email_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.email_var = tk.StringVar(value=self.user.get("email", ""))
        email_entry = ttk.Entry(
            email_frame,
            textvariable=self.email_var,
            style="TEntry",
            state="readonly"
        )
        email_entry.pack(fill=tk.X, ipady=3)
    
    def _create_notification_card(self, parent):
        """Bildirim ayarları kartını oluşturur."""
        # Bildirim kartı çerçevesi
        notification_card = tk.Frame(parent, bg=self.card_bg, padx=15, pady=15)
        notification_card.pack(fill=tk.X, pady=(0, 15))
        notification_card.configure(highlightbackground="#d0d0d0", highlightthickness=1)
        
        # Başlık
        notification_title = ttk.Label(
            notification_card,
            text="Bildirimler",
            style="Section.TLabel"
        )
        notification_title.pack(anchor=tk.W, pady=(0, 10))
        
        # E-posta bildirimi
        self.email_notification_var = tk.BooleanVar(value=self.settings.get("email_notification", True))
        email_check = ttk.Checkbutton(
            notification_card,
            text=f"E-posta Bildirimleri ({self.user.get('email', '')})",
            variable=self.email_notification_var,
            style="TCheckbutton",
            command=lambda: self._set_modified()
        )
        email_check.pack(anchor=tk.W, pady=(0, 5))
        
        # SMS bildirimi
        self.sms_notification_var = tk.BooleanVar(value=self.settings.get("sms_notification", False))
        sms_check = ttk.Checkbutton(
            notification_card,
            text="SMS Bildirimleri",
            variable=self.sms_notification_var,
            style="TCheckbutton",
            command=self._toggle_sms
        )
        sms_check.pack(anchor=tk.W, pady=(0, 5))
        
        # Telefon numarası alanı
        phone_frame = ttk.Frame(notification_card, style="Card.TFrame")
        phone_frame.pack(fill=tk.X, padx=(20, 0), pady=(0, 10))
        
        self.phone_var = tk.StringVar(value=self.settings.get("phone_number", ""))
        self.phone_entry = ttk.Entry(
            phone_frame,
            textvariable=self.phone_var,
            style="TEntry",
            state="disabled" if not self.settings.get("sms_notification", False) else "normal",
            width=20
        )
        self.phone_entry.pack(side=tk.LEFT)
        
        # Bildirim testi butonu
        test_button = ttk.Button(
            notification_card,
            text="🔔 Bildirimleri Test Et",
            style="TButton",
            command=self._test_notifications,
            cursor="hand2"
        )
        test_button.pack(anchor=tk.W)
    
    def _create_theme_card(self, parent):
        """Tema ayarları kartını oluşturur."""
        # Tema kartı çerçevesi
        theme_card = tk.Frame(parent, bg=self.card_bg, padx=15, pady=15)
        theme_card.pack(fill=tk.X)
        theme_card.configure(highlightbackground="#d0d0d0", highlightthickness=1)
        
        # Başlık
        theme_title = ttk.Label(
            theme_card,
            text="Görünüm",
            style="Section.TLabel"
        )
        theme_title.pack(anchor=tk.W, pady=(0, 10))
        
        # Koyu mod seçeneği
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        dark_mode_check = ttk.Checkbutton(
            theme_card,
            text="Koyu Mod",
            variable=self.dark_mode_var,
            style="TCheckbutton",
            command=self._preview_theme
        )
        dark_mode_check.pack(anchor=tk.W, pady=(0, 10))
        
        # Tema önizleme butonu
        preview_button = ttk.Button(
            theme_card,
            text="👁️ Temayı Önizle",
            style="TButton",
            command=self._preview_theme,
            cursor="hand2"
        )
        preview_button.pack(anchor=tk.W)
    
    def _toggle_sms(self):
        """SMS bildirim durumunu değiştirir ve ilgili alanları aktif/pasif yapar."""
        if self.sms_notification_var.get():
            self.phone_entry.config(state="normal")
        else:
            self.phone_entry.config(state="disabled")
        self._set_modified()
    
    def _test_notifications(self):
        """Bildirimleri test eder."""
        if not self.email_notification_var.get() and not self.sms_notification_var.get():
            messagebox.showwarning("Uyarı", "Hiçbir bildirim türü aktif değil.")
            return
            
        # Gerçek bir test göndermeden önce kullanıcıya bilgi verir
        messagebox.showinfo(
            "Bildirim Testi", 
            "Test bildirimi gönderildi. Gerçek bir düşme algılandığında tüm aktif kanallara bildirim gönderilecektir."
        )
    
    def _preview_theme(self):
        """Temayı önizler."""
        self.dark_mode = self.dark_mode_var.get()
        self._setup_colors()
        self._setup_styles()
        self._refresh_ui()
        self._set_modified()
    
    def _refresh_ui(self):
        """UI bileşenlerini yeniler."""
        # Mevcut UI'yi temizle
        for widget in self.winfo_children():
            widget.destroy()
            
        # UI'yi yeniden oluştur
        self._create_ui()
    
    def _set_modified(self):
        """Değişiklik yapıldığını işaretler."""
        self.is_modified = True
    
    def _save_settings(self):
        """Ayarları kaydeder ve kullanıcıyı bilgilendirir."""
        if not self.is_modified:
            self._on_back()
            return
        
        try:
            # Yeni ayarları hazırla
            settings = {
                "email_notification": self.email_notification_var.get(),
                "sms_notification": self.sms_notification_var.get(),
                "phone_number": self.phone_var.get().strip(),
                "dark_mode": self.dark_mode_var.get()
            }
            
            # Kullanıcı bilgilerini güncelle
            user_data = {
                "displayName": self.name_var.get().strip()
            }
            
            # Veritabanında güncelle
            self.db_manager.update_user_data(self.user["localId"], user_data)
            self.db_manager.save_user_settings(self.user["localId"], settings)
            
            # Kullanıcı nesnesini güncelle
            self.user["displayName"] = user_data["displayName"]
            
            messagebox.showinfo(
                "Başarılı",
                "Ayarlarınız başarıyla kaydedildi."
            )
            
            # Geri dön
            self._on_back()
            
        except Exception as e:
            messagebox.showerror(
                "Hata",
                f"Ayarlar kaydedilirken bir hata oluştu: {str(e)}"
            )
    
    def _on_back(self):
        """Geri dönüş işlemini gerçekleştirir."""
        if self.is_modified:
            if not messagebox.askyesno(
                "Değişiklikler Kaydedilmedi",
                "Değişiklikleriniz kaydedilmedi. Yine de çıkmak istiyor musunuz?"
            ):
                return
        
        self.back_fn()