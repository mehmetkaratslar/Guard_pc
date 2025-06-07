import tkinter as tk
from tkinter import ttk, messagebox
import logging
import threading
import os
import math
import time
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageDraw
import re
import random

class LoginFrame(tk.Frame):
    """Şık, cana yakın ve güven veren modern giriş ekranı."""

    def __init__(self, parent, auth, on_login_success, on_register_click=None):
        super().__init__(parent, bg="#FFFFFF")
        self.parent = parent
        self.auth = auth
        self.on_login_success = on_login_success
        self.on_register_click = on_register_click
        
        # Değişkenleri başlangıçta tanımla
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.remember_var = tk.BooleanVar(value=True)
        
        # Animasyon değişkenleri
        self.anim_ids = []
        self.bubble_particles = []
        
        # Google giriş durumu takibi
        self.google_login_in_progress = False
        
        # Renk paleti - sıcak ve güven veren renkler
        self.colors = {
            'primary': "#4285F4",      # Google mavi
            'primary_dark': "#3367D6",
            'primary_light': "#5E97F6",
            'secondary': "#FBBC05",    # Sıcak sarı
            'success': "#34A853",      # Yeşil
            'danger': "#EA4335",       # Kırmızı
            'warning': "#FF9800",      # Turuncu
            'light_bg': "#F8F9FA",     # Açık gri arka plan
            'card_bg': "#FFFFFF",      # Kart arka planı
            'text': "#202124",         # Koyu metin
            'text_secondary': "#5F6368", # İkincil metin
            'border': "#DADCE0",       # Çerçeve rengi
            'bubble_color1': "#E8F0FE", # Baloncuk rengi 1
            'bubble_color2': "#F1F3F4", # Baloncuk rengi 2
            'bubble_color3': "#D2E3FC"  # Baloncuk rengi 3
        }
        
        # Kayan baloncuklar için renk paleti
        self.bubble_colors = [
            self.colors['bubble_color1'],
            self.colors['bubble_color2'],
            self.colors['bubble_color3'],
            "#E6F4EA",  # Açık yeşil
            "#FCE8E6",  # Açık kırmızı
            "#FEF7E0"   # Açık sarı
        ]
        
        # UI oluştur
        self._create_ui()
        
        # Animasyonları başlat
        self._create_floating_bubbles()
        self._animate_bubbles()
        
        # Ekran yeniden boyutlandırıldığında uyum sağla
        self.bind("<Configure>", self._on_resize)
    
    def _create_ui(self):
        """Temel UI yapısını oluşturur"""
        # Ana çerçeveyi oluştur
        self.main_frame = tk.Frame(self, bg=self.colors['light_bg'])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sol panel - kayan baloncuklar ve marka mesajı
        self.left_panel = tk.Frame(self.main_frame, bg=self.colors['light_bg'], width=600)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Baloncuk arkaplanı için canvas
        self.bubble_canvas = tk.Canvas(self.left_panel, bg=self.colors['light_bg'], 
                                      highlightthickness=0)
        self.bubble_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Marka mesajı çerçevesi
        self.brand_frame = tk.Frame(self.bubble_canvas, bg=self.colors['light_bg'])
        
        # Logo
        self._create_logo(self.brand_frame)
        
        # Marka sloganı
        slogan_frame = tk.Frame(self.brand_frame, bg=self.colors['light_bg'], padx=30, pady=20)
        slogan_frame.pack(fill=tk.X)
        
        main_slogan = tk.Label(slogan_frame, 
                             text="Güvenliğiniz İçin\nYanınızdayız", 
                             font=("Segoe UI", 32, "bold"), 
                             fg=self.colors['primary'], 
                             bg=self.colors['light_bg'],
                             justify=tk.LEFT)
        main_slogan.pack(anchor=tk.W)
        
        sub_slogan = tk.Label(slogan_frame, 
                            text="Tek tuşla güvende kalın, hayatınızı kolaylaştırın.", 
                            font=("Segoe UI", 16), 
                            fg=self.colors['text_secondary'], 
                            bg=self.colors['light_bg'],
                            justify=tk.LEFT,
                            wraplength=400)
        sub_slogan.pack(anchor=tk.W, pady=(15, 0))
        
        # Canvas üzerinde brand_frame için pencere oluştur
        self.brand_window = self.bubble_canvas.create_window(50, 50, 
                                                           anchor=tk.NW, 
                                                           window=self.brand_frame)
        
        # Sağ panel - giriş formu
        self.right_panel = tk.Frame(self.main_frame, bg=self.colors['card_bg'], padx=40, pady=40)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)
        
        # Giriş formu
        self._create_login_form()
    
    def _create_logo(self, parent):
        """Logo alanını oluşturur"""
        logo_frame = tk.Frame(parent, bg=self.colors['light_bg'], padx=30, pady=30)
        logo_frame.pack(anchor=tk.W)
        
        # Logo yükleme
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    "resources", "icons", "logo.png")
            
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                img = img.resize((80, 80), Image.LANCZOS)
                
                # Parlaklık ve kontrast ayarları
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.2)
                
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)
                
                self.logo_image = ImageTk.PhotoImage(img)
                logo_img = tk.Label(logo_frame, image=self.logo_image, bg=self.colors['light_bg'])
                logo_img.pack(side=tk.LEFT)
                
                # Logo adı
                logo_text = tk.Label(logo_frame, text="Guard", 
                                   font=("Segoe UI", 30, "bold"), 
                                   fg=self.colors['primary'],
                                   bg=self.colors['light_bg'])
                logo_text.pack(side=tk.LEFT, padx=(15, 0))
        except Exception as e:
            logging.warning(f"Logo yüklenemedi: {str(e)}")
            # Fallback - metin logo
            logo_text = tk.Label(logo_frame, text="G", 
                               font=("Segoe UI", 40, "bold"), 
                               fg=self.colors['primary'],
                               bg=self.colors['light_bg'])
            logo_text.pack(side=tk.LEFT)
            
            logo_name = tk.Label(logo_frame, text="Guard", 
                               font=("Segoe UI", 30, "bold"), 
                               fg=self.colors['primary'],
                               bg=self.colors['light_bg'])
            logo_name.pack(side=tk.LEFT, padx=(15, 0))
    
    def _create_login_form(self):
        """Giriş formunu oluşturur"""
        # Form başlığı
        header_frame = tk.Frame(self.right_panel, bg=self.colors['card_bg'])
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        welcome_label = tk.Label(header_frame, 
                               text="Hoş Geldiniz", 
                               font=("Segoe UI", 28, "bold"), 
                               fg=self.colors['text'], 
                               bg=self.colors['card_bg'])
        welcome_label.pack(anchor=tk.W)
        
        subtitle_label = tk.Label(header_frame, 
                                text="Hesabınıza giriş yapın", 
                                font=("Segoe UI", 14), 
                                fg=self.colors['text_secondary'], 
                                bg=self.colors['card_bg'])
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Form alanları
        form_frame = tk.Frame(self.right_panel, bg=self.colors['card_bg'])
        form_frame.pack(fill=tk.X, pady=(0, 20))
        
        # E-posta alanı
        email_frame = tk.Frame(form_frame, bg=self.colors['card_bg'])
        email_frame.pack(fill=tk.X, pady=(0, 20))
        
        email_label = tk.Label(email_frame, 
                             text="E-posta", 
                             font=("Segoe UI", 12, "bold"), 
                             fg=self.colors['text'], 
                             bg=self.colors['card_bg'])
        email_label.pack(anchor=tk.W, pady=(0, 8))
        
        # Giriş çerçevesi - yumuşak kenarlıklı
        email_input_frame = tk.Frame(email_frame, 
                                   bg=self.colors['card_bg'], 
                                   highlightbackground=self.colors['border'],
                                   highlightthickness=1,
                                   bd=0)
        email_input_frame.pack(fill=tk.X)
        
        # Simge
        email_icon_frame = tk.Frame(email_input_frame, bg=self.colors['card_bg'], padx=10, pady=10)
        email_icon_frame.pack(side=tk.LEFT)
        
        email_icon = tk.Label(email_icon_frame, 
                            text="📧", 
                            font=("Segoe UI", 14), 
                            fg=self.colors['text_secondary'], 
                            bg=self.colors['card_bg'])
        email_icon.pack()
        
        # Giriş alanı
        self.email_entry = tk.Entry(email_input_frame, 
                                 textvariable=self.email_var,
                                 font=("Segoe UI", 14), 
                                 fg=self.colors['text'], 
                                 bg=self.colors['card_bg'],
                                 relief="flat", 
                                 bd=0, 
                                 highlightthickness=0)
        self.email_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        # Odak durumunda kenar rengini değiştir
        self.email_entry.bind("<FocusIn>", lambda e: self._on_entry_focus(email_input_frame, True))
        self.email_entry.bind("<FocusOut>", lambda e: self._on_entry_focus(email_input_frame, False))
        
        # Şifre alanı
        password_frame = tk.Frame(form_frame, bg=self.colors['card_bg'])
        password_frame.pack(fill=tk.X, pady=(0, 10))
        
        password_label = tk.Label(password_frame, 
                                text="Şifre", 
                                font=("Segoe UI", 12, "bold"), 
                                fg=self.colors['text'], 
                                bg=self.colors['card_bg'])
        password_label.pack(anchor=tk.W, pady=(0, 8))
        
        # Şifre giriş çerçevesi
        password_input_frame = tk.Frame(password_frame, 
                                      bg=self.colors['card_bg'], 
                                      highlightbackground=self.colors['border'],
                                      highlightthickness=1,
                                      bd=0)
        password_input_frame.pack(fill=tk.X)
        
        # Şifre simgesi
        password_icon_frame = tk.Frame(password_input_frame, bg=self.colors['card_bg'], padx=10, pady=10)
        password_icon_frame.pack(side=tk.LEFT)
        
        password_icon = tk.Label(password_icon_frame, 
                               text="🔒", 
                               font=("Segoe UI", 14), 
                               fg=self.colors['text_secondary'], 
                               bg=self.colors['card_bg'])
        password_icon.pack()
        
        # Şifre giriş alanı
        self.password_entry = tk.Entry(password_input_frame, 
                                    textvariable=self.password_var,
                                    font=("Segoe UI", 14), 
                                    fg=self.colors['text'], 
                                    bg=self.colors['card_bg'],
                                    relief="flat", 
                                    bd=0, 
                                    highlightthickness=0,
                                    show="•")
        self.password_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        # Şifreyi göster/gizle butonu
        self.show_password = False
        
        def toggle_password():
            self.show_password = not self.show_password
            self.password_entry.config(show="" if self.show_password else "•")
            password_toggle.config(text="👁️" if self.show_password else "👁️‍🗨️")
        
        password_toggle = tk.Label(password_input_frame, 
                                 text="👁️‍🗨️", 
                                 font=("Segoe UI", 14), 
                                 fg=self.colors['text_secondary'], 
                                 bg=self.colors['card_bg'],
                                 cursor="hand2")
        password_toggle.pack(side=tk.RIGHT, padx=10, pady=10)
        password_toggle.bind("<Button-1>", lambda e: toggle_password())
        
        # Odak durumunda kenar rengini değiştir
        self.password_entry.bind("<FocusIn>", lambda e: self._on_entry_focus(password_input_frame, True))
        self.password_entry.bind("<FocusOut>", lambda e: self._on_entry_focus(password_input_frame, False))
        
        # Beni hatırla ve şifremi unuttum
        options_frame = tk.Frame(form_frame, bg=self.colors['card_bg'])
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Beni hatırla
        remember_checkbox = tk.Checkbutton(options_frame, 
                                        text="Beni hatırla", 
                                        font=("Segoe UI", 12), 
                                        fg=self.colors['text'], 
                                        bg=self.colors['card_bg'],
                                        activebackground=self.colors['card_bg'],
                                        variable=self.remember_var,
                                        cursor="hand2")
        remember_checkbox.pack(side=tk.LEFT)
        
        # Şifremi unuttum bağlantısı
        forgot_link = tk.Label(options_frame, 
                             text="Şifremi unuttum", 
                             font=("Segoe UI", 12, "underline"), 
                             fg=self.colors['primary'], 
                             bg=self.colors['card_bg'],
                             cursor="hand2")
        forgot_link.pack(side=tk.RIGHT)
        forgot_link.bind("<Button-1>", self._forgot_password_click)
        
        # Giriş butonları
        buttons_frame = tk.Frame(form_frame, bg=self.colors['card_bg'])
        buttons_frame.pack(fill=tk.X, pady=(10, 20))
        
        # Giriş yap butonu - yuvarlak köşeli
        self.login_button = tk.Button(buttons_frame, 
                               text="Giriş Yap", 
                               font=("Segoe UI", 14, "bold"), 
                               fg="#FFFFFF", 
                               bg=self.colors['primary'],
                               activebackground=self.colors['primary_dark'],
                               activeforeground="#FFFFFF",
                               relief="flat", 
                               bd=0, 
                               padx=15, 
                               pady=12,
                               command=self._on_login,
                               cursor="hand2")
        self.login_button.pack(fill=tk.X)
        
        # Hover efekti
        self.login_button.bind("<Enter>", lambda e: self.login_button.config(bg=self.colors['primary_dark']))
        self.login_button.bind("<Leave>", lambda e: self.login_button.config(bg=self.colors['primary']))
        
        # Ayırıcı
        divider_frame = tk.Frame(form_frame, bg=self.colors['card_bg'], pady=10)
        divider_frame.pack(fill=tk.X)
        
        divider_left = tk.Frame(divider_frame, height=1, bg=self.colors['border'])
        divider_left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        divider_text = tk.Label(divider_frame, 
                              text="veya", 
                              font=("Segoe UI", 12), 
                              fg=self.colors['text_secondary'], 
                              bg=self.colors['card_bg'])
        divider_text.pack(side=tk.LEFT)
        
        divider_right = tk.Frame(divider_frame, height=1, bg=self.colors['border'])
        divider_right.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Google ile giriş butonu
        google_button_frame = tk.Frame(form_frame, bg=self.colors['card_bg'], pady=10)
        google_button_frame.pack(fill=tk.X)
        
        # Google butonu - yuvarlak köşeli, kenarlıklı
        self.google_button = tk.Button(google_button_frame, 
                                text="Google ile Giriş Yap", 
                                font=("Segoe UI", 14), 
                                fg=self.colors['text'], 
                                bg=self.colors['card_bg'],
                                activebackground=self.colors['light_bg'],
                                activeforeground=self.colors['text'],
                                relief="flat", 
                                bd=1, 
                                padx=15, 
                                pady=12,
                                command=self._google_login,
                                cursor="hand2")
        self.google_button.pack(fill=tk.X)
        
        # Google simgesi ekle
        try:
            google_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                           "resources", "icons", "google_icon.png")
            
            if os.path.exists(google_icon_path):
                google_img = Image.open(google_icon_path).resize((20, 20), Image.LANCZOS)
                self.google_icon = ImageTk.PhotoImage(google_img)
                
                # Simge pozisyonunu ayarla
                self.google_button.config(image=self.google_icon, compound=tk.LEFT, padx=15)
        except Exception as e:
            logging.warning(f"Google ikonu yüklenemedi: {str(e)}")
            # Fallback - G harfi 
            self.google_button.config(text="G | Google ile Giriş Yap")
        
        # Hesap oluştur bağlantısı
        register_frame = tk.Frame(form_frame, bg=self.colors['card_bg'], pady=10)
        register_frame.pack(fill=tk.X)
        
        register_text = tk.Label(register_frame, 
                               text="Hesabınız yok mu? ", 
                               font=("Segoe UI", 12), 
                               fg=self.colors['text'], 
                               bg=self.colors['card_bg'])
        register_text.pack(side=tk.LEFT)
        
        register_link = tk.Label(register_frame, 
                               text="Hemen kaydolun", 
                               font=("Segoe UI", 12, "bold", "underline"), 
                               fg=self.colors['primary'], 
                               bg=self.colors['card_bg'],
                               cursor="hand2")
        register_link.pack(side=tk.LEFT)
        register_link.bind("<Button-1>", self._on_register_click)
        
        # Durum ve ilerleme çubuğu
        self.status_frame = tk.Frame(self.right_panel, bg=self.colors['card_bg'])
        
        # İlerleme çubuğu stil ayarları
        style = ttk.Style()
        style.configure("TProgressbar", 
                      thickness=3, 
                      troughcolor=self.colors['light_bg'],
                      background=self.colors['primary'])
        
        self.progress_bar = ttk.Progressbar(self.status_frame, 
                                          style="TProgressbar", 
                                          mode="indeterminate", 
                                          length=100)
        self.progress_bar.pack(fill=tk.X)
        
        # Durum mesajı
        self.status_label = tk.Label(self.status_frame, 
                                   text="", 
                                   font=("Segoe UI", 11), 
                                   fg=self.colors['primary'], 
                                   bg=self.colors['card_bg'])
        self.status_label.pack(pady=5)
        
        # Başlangıçta gizle
        self.status_frame.pack_forget()
    
    def _on_entry_focus(self, frame, is_focused):
        """Giriş alanı odak değiştiğinde çerçeve rengini değiştirir"""
        if is_focused:
            frame.config(highlightbackground=self.colors['primary'])
        else:
            frame.config(highlightbackground=self.colors['border'])
    
    def _forgot_password_click(self, event=None):
        """Şifremi unuttum bağlantısına tıklandığında"""
        email = self.email_var.get().strip()
        if not email:
            self._show_status("Şifre sıfırlama için önce e-posta adresinizi girin", "warning")
            self.email_entry.focus()
            return
            
        if not self._validate_email(email):
            self._show_status("Geçerli bir e-posta adresi girin", "error")
            self.email_entry.focus()
            return
        
        # Şifre sıfırlama işlemini başlat
        result = messagebox.askyesno(
            "Şifre Sıfırlama", 
            f"Şifre sıfırlama bağlantısı {email} adresine gönderilsin mi?"
        )
        
        if result:
            self._show_progress(True, "Şifre sıfırlama bağlantısı gönderiliyor...")
            threading.Thread(target=self._send_password_reset, args=(email,), daemon=True).start()
    
    def _send_password_reset(self, email):
        """Şifre sıfırlama e-postası gönderir"""
        try:
            self.auth.send_password_reset_email(email)
            self.after(0, lambda: self._show_status("Şifre sıfırlama bağlantısı e-posta adresinize gönderildi", "success"))
            self.after(0, lambda: self._show_progress(False))
        except Exception as e:
            self.after(0, lambda: self._show_status(f"Şifre sıfırlama e-postası gönderilemedi: {str(e)}", "error"))
            self.after(0, lambda: self._show_progress(False))
    
    def _create_floating_bubbles(self):
        """Kayan baloncukları oluşturur"""
        width = self.bubble_canvas.winfo_width() or 600
        height = self.bubble_canvas.winfo_height() or 800
        
        # 15-25 arası rastgele baloncuk oluştur
        num_bubbles = 20
        
        for i in range(num_bubbles):
            # Rastgele boyut, pozisyon ve renk
            size = 30 + int(100 * (i / num_bubbles))  # Boyut: 30-130 piksel
            opacity = 0.5 + (0.4 * i / num_bubbles)  # Opaklık: 0.5-0.9
            
            x = width * (0.1 + 0.8 * (i / num_bubbles))
            y = height * (0.1 + 0.8 * i / num_bubbles)
            
            # Rastgele hareket yönü ve hızı
            speed_x = (0.3 + 0.5 * (i / num_bubbles)) * (1 if i % 2 == 0 else -1)
            speed_y = (0.2 + 0.4 * (i / num_bubbles)) * (1 if i % 3 == 0 else -1)
            
            # Rastgele renk
            color_idx = i % len(self.bubble_colors)
            
            bubble = {
                'x': x,
                'y': y,
                'size': size,
                'speed_x': speed_x,
                'speed_y': speed_y,
                'color': self.bubble_colors[color_idx],
                'opacity': opacity,
                'pulse': 0  # Nabız efekti için
            }
            
            self.bubble_particles.append(bubble)
    
    def _animate_bubbles(self):
        """Baloncukları hareket ettirir ve çizer"""
        try:
            width = self.bubble_canvas.winfo_width()
            height = self.bubble_canvas.winfo_height()
            
            if width > 1 and height > 1:  # Geçerli boyutlar
                # Canvas'ı temizle
                self.bubble_canvas.delete("bubble")
                
                # Her baloncuğu güncelle ve çiz
                for bubble in self.bubble_particles:
                    # Baloncukları hareket ettir
                    bubble['x'] += bubble['speed_x']
                    bubble['y'] += bubble['speed_y']
                    
                    # Nabız efekti - boyutunu 0.9-1.1 arasında değiştir
                    bubble['pulse'] += 0.05
                    pulse_factor = 1.0 + 0.1 * math.sin(bubble['pulse'])
                    
                    # Sınırları kontrol et ve yön değiştir
                    if bubble['x'] < 0 or bubble['x'] > width:
                        bubble['speed_x'] *= -1
                    if bubble['y'] < 0 or bubble['y'] > height:
                        bubble['speed_y'] *= -1
                    
                    # Boyutu hesapla
                    size = bubble['size'] * pulse_factor
                    
                    # Baloncuğu çiz - yuvarlak
                    self.bubble_canvas.create_oval(
                        bubble['x'] - size/2, bubble['y'] - size/2,
                        bubble['x'] + size/2, bubble['y'] + size/2,
                        fill=bubble['color'],
                        outline="",
                        stipple="gray50" if bubble['opacity'] < 0.9 else "",
                        tags="bubble"
                    )
            
            # Animasyonu devam ettir
            anim_id = self.after(50, self._animate_bubbles)
            self.anim_ids.append(anim_id)
            
        except Exception as e:
            logging.error(f"Baloncuk animasyonu hatası: {str(e)}")
    
    def _on_resize(self, event=None):
        """Ekran boyutu değiştiğinde arayüzü günceller"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width > 100 and height > 100:  # Geçerli boyutlar
            # Sağ ve sol panel genişlikleri
            if width >= 1200:  # Geniş ekran
                left_width = int(width * 0.6)
                right_width = width - left_width
                
                # Sol panel görünür
                if not self.left_panel.winfo_ismapped():
                    self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                self.left_panel.config(width=left_width)
                self.right_panel.config(width=right_width)
                
                # Marka çerçevesi konumu güncelle
                brand_height = self.brand_frame.winfo_reqheight()
                if brand_height > 0:
                    self.bubble_canvas.coords(self.brand_window, 50, height / 2 - brand_height / 2)
                
            elif width >= 800:  # Orta ekran
                left_width = int(width * 0.5)
                right_width = width - left_width
                
                # Sol panel görünür
                if not self.left_panel.winfo_ismapped():
                    self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                self.left_panel.config(width=left_width)
                self.right_panel.config(width=right_width)
                
                # Marka çerçevesi konumu güncelle
                brand_height = self.brand_frame.winfo_reqheight()
                if brand_height > 0:
                    self.bubble_canvas.coords(self.brand_window, 30, height / 2 - brand_height / 2)
                
            else:  # Dar ekran - sadece form göster
                # Sol paneli gizle
                if self.left_panel.winfo_ismapped():
                    self.left_panel.pack_forget()
                self.right_panel.config(width=width)
            
            # Yeni baloncuklar oluştur
            if len(self.bubble_particles) > 0:
                self.bubble_particles.clear()
                self._create_floating_bubbles()
    
    def _on_login(self):
        """Giriş butonuna tıklandığında"""
        email = self.email_var.get().strip()
        password = self.password_var.get()
        
        # Basit doğrulama
        if not email:
            self._show_status("Lütfen e-posta adresinizi girin", "error")
            self._shake_widget(self.email_entry)
            return
        
        if not password:
            self._show_status("Lütfen şifrenizi girin", "error")
            self._shake_widget(self.password_entry)
            return
        
        # E-posta format kontrolü
        if not self._validate_email(email):
            self._show_status("Geçersiz e-posta formatı", "error")
            self._shake_widget(self.email_entry)
            return
        
        # İlerleme çubuğunu göster
        self._show_progress(True, "Giriş yapılıyor...")
        
        # Giriş işlemini başlat
        threading.Thread(target=self._login_process, 
                         args=(email, password), 
                         daemon=True).start()
    
    def _login_process(self, email, password):
        """Giriş işlemini gerçekleştirir"""
        try:
            # Firebase ile giriş
            user = self.auth.sign_in_with_email_password(email, password)
            
            # Kısa bir gecikme ekle (animasyon için)
            time.sleep(0.8)
            
            # Giriş başarılıysa
            self.after(0, lambda: self._handle_login_success(user))
            
        except Exception as e:
            error_msg = str(e)
            
            # Kullanıcı dostu hata mesajları
            if "INVALID_LOGIN_CREDENTIALS" in error_msg:
                error_msg = "E-posta veya şifre hatalı"
            elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_msg:
                error_msg = "Çok fazla başarısız deneme. Lütfen daha sonra tekrar deneyin"
            elif "USER_DISABLED" in error_msg:
                error_msg = "Bu hesap devre dışı bırakılmış"
            
            self.after(0, lambda: self._show_status(error_msg, "error"))
            self.after(0, lambda: self._show_progress(False))
    
    def _google_login(self):
        """Google ile giriş"""
        if self.google_login_in_progress:
            self._show_status("Google giriş işlemi zaten devam ediyor", "info")
            return
            
        self.google_login_in_progress = True
        self._show_progress(True, "Google ile bağlanılıyor...")
        
        # Google butonu devre dışı bırak
        self.google_button.config(state="disabled")
        
        threading.Thread(target=self._google_login_process, daemon=True).start()
    
    def _google_login_process(self):
        """Google giriş işlemini gerçekleştirir"""
        try:
            # Google OAuth sürecini başlat
            logging.info("Google OAuth süreci başlatılıyor...")
            auth_url, auth_code = self.auth.sign_in_with_google()
            
            if not auth_code:
                raise Exception("Yetkilendirme kodu alınamadı")
                
            logging.info("Yetkilendirme kodu alındı, Firebase'e giriş yapılıyor...")
            
            # Firebase'e Google ile giriş yap
            user = self.auth.complete_google_sign_in(None, auth_code)
            
            # Giriş başarılı
            self.after(0, lambda: self._handle_login_success(user))
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Google giriş hatası: {error_msg}")
            
            # Kullanıcı dostu hata mesajları
            if "iptal edildi" in error_msg.lower() or "cancel" in error_msg.lower():
                error_msg = "Google giriş işlemi iptal edildi"
            elif "zaman aşımı" in error_msg.lower() or "timeout" in error_msg.lower():
                error_msg = "Google giriş zaman aşımına uğradı"
            elif "bağlantı" in error_msg.lower():
                error_msg = "İnternet bağlantısı hatası"
            else:
                error_msg = f"Google giriş hatası: {error_msg}"
            
            self.after(0, lambda: self._show_status(error_msg, "error"))
            self.after(0, lambda: self._show_progress(False))
            self.after(0, self._enable_google_button)
        finally:
            self.google_login_in_progress = False
    
    def _enable_google_button(self):
        """Google butonunu tekrar etkinleştir"""
        try:
            self.google_button.config(state="normal")
        except:
            pass
    
    def _handle_login_success(self, user):
        """Giriş başarılı olduğunda - güvenli callback"""
        try:
            logging.info(f"Giriş başarılı: {user.get('email', '')}")
            
            # Durum güncelle
            self._show_status("Giriş başarılı! Yönlendiriliyorsunuz...", "success")
            
            # Başarı animasyonu
            self._show_success_animation()
            
            # Google butonunu tekrar etkinleştir
            self._enable_google_button()
            
            # 🔧 Güvenli callback çağırma
            def safe_callback():
                """Güvenli callback wrapper"""
                try:
                    if self.on_login_success and callable(self.on_login_success):
                        self.on_login_success(user)
                except Exception as e:
                    logging.error(f"Login callback hatası: {e}")
            
            # Callback'i güvenli şekilde çağır
            self.after(1500, safe_callback)
            
        except Exception as e:
            logging.error(f"Handle login success hatası: {e}")
    
    def _on_register_click(self, event=None):
        """Kayıt ol bağlantısına tıklandığında"""
        logging.info("Kayıt ol bağlantısına tıklandı")
        
        # Kayıt ekranına git
        if self.on_register_click:
            self.on_register_click()
        else:
            self._show_status("Kayıt ekranı açılamadı", "error")
    
    def _show_success_animation(self):
        """Başarılı giriş animasyonu"""
        # Form alanlarını temizle
        for widget in self.right_panel.winfo_children():
            widget.destroy()
        
        # Başarı çerçevesi
        success_frame = tk.Frame(self.right_panel, bg=self.colors['card_bg'], padx=40, pady=40)
        success_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tik işareti animasyonu
        check_canvas = tk.Canvas(success_frame, width=150, height=150, 
                               bg=self.colors['card_bg'], highlightthickness=0)
        check_canvas.pack(pady=(50, 30))
        
        # Çember çiz
        check_canvas.create_oval(10, 10, 140, 140, 
                               outline=self.colors['success'], 
                               width=5)
        
        # Tik işareti çiz - animasyonlu
        self._animate_checkmark(check_canvas)
        
        # Başarı mesajı
        success_title = tk.Label(success_frame, 
                               text="Giriş Başarılı!", 
                               font=("Segoe UI", 26, "bold"), 
                               fg=self.colors['success'], 
                               bg=self.colors['card_bg'])
        success_title.pack(pady=(0, 20))
        
        # Kullanıcı bilgisi
        welcome_label = tk.Label(success_frame, 
                               text="Hoş geldiniz, güvenliğiniz için yanınızdayız.", 
                               font=("Segoe UI", 14), 
                               fg=self.colors['text'], 
                               bg=self.colors['card_bg'])
        welcome_label.pack(pady=(0, 30))
        
        # İlerleme çubuğu
        progress_frame = tk.Frame(success_frame, bg=self.colors['card_bg'])
        progress_frame.pack(fill=tk.X, pady=(20, 0))
        
        redirect_label = tk.Label(progress_frame, 
                                text="Yönlendiriliyorsunuz...", 
                                font=("Segoe UI", 12), 
                                fg=self.colors['text_secondary'], 
                                bg=self.colors['card_bg'])
        redirect_label.pack()
        
        redirect_progress = ttk.Progressbar(progress_frame, 
                                          mode="indeterminate", 
                                          length=100)
        redirect_progress.pack(fill=tk.X, pady=(10, 0))
        redirect_progress.start(15)
    
    def _animate_checkmark(self, canvas):
        """Tik işareti animasyonu"""
        # Tik işareti için nokta koordinatları
        points = [
            [40, 80],  # Başlangıç
            [65, 100], # Orta
            [110, 50]  # Bitiş
        ]
        
        # İlk çizgi - sol üstten orta noktaya
        def animate_first_line(step=0, max_step=20):
            if step <= max_step:
                # İlerleme
                progress = step / max_step
                
                # Noktalar arası interpolasyon
                x1 = points[0][0]
                y1 = points[0][1]
                x2 = points[0][0] + (points[1][0] - points[0][0]) * progress
                y2 = points[0][1] + (points[1][1] - points[0][1]) * progress
                
                # Çizgiyi temizle ve yeniden çiz
                canvas.delete("tick_line1")
                canvas.create_line(x1, y1, x2, y2, 
                                 fill=self.colors['success'], 
                                 width=8, 
                                 capstyle="round", 
                                 tags="tick_line1")
                
                # Sonraki adımı planla
                anim_id = canvas.after(10, lambda: animate_first_line(step + 1, max_step))
                self.anim_ids.append(anim_id)
            else:
                # İlk çizgi tamamlandı, ikinci çizgiyi başlat
                animate_second_line()
        
        # İkinci çizgi - orta noktadan sağ üste
        def animate_second_line(step=0, max_step=20):
            if step <= max_step:
                # İlerleme
                progress = step / max_step
                
                # Noktalar arası interpolasyon
                x1 = points[1][0]
                y1 = points[1][1]
                x2 = points[1][0] + (points[2][0] - points[1][0]) * progress
                y2 = points[1][1] + (points[2][1] - points[1][1]) * progress
                
                # Çizgiyi temizle ve yeniden çiz
                canvas.delete("tick_line2")
                canvas.create_line(x1, y1, x2, y2, 
                                 fill=self.colors['success'], 
                                 width=8, 
                                 capstyle="round", 
                                 tags="tick_line2")
                
                # Sonraki adımı planla
                anim_id = canvas.after(10, lambda: animate_second_line(step + 1, max_step))
                self.anim_ids.append(anim_id)
        
        # Animasyon başlat
        animate_first_line()
    
    def _shake_widget(self, widget):
        """Hatalı giriş için sarsma animasyonu"""
        original_x = widget.winfo_x()
        
        def shake(step=0, distance=10, direction=1):
            if step < 10:
                # Widget'ı hareket ettir
                current_distance = distance * (10 - step) / 10
                widget.place(x=original_x + current_distance * direction)
                
                # Sonraki adımı planla
                anim_id = self.after(30, lambda: shake(step + 1, distance, -direction))
                self.anim_ids.append(anim_id)
            else:
                # Original pozisyona geri getir
                widget.place(x=original_x)
        
        # Animasyonu başlat
        shake()
    
    def _show_status(self, message, status_type="info"):
        """Durum mesajını gösterir"""
        try:
            # Renk belirle
            if status_type == "success":
                color = self.colors['success']
            elif status_type == "error":
                color = self.colors['danger']
            elif status_type == "warning":
                color = self.colors['warning']
            else:  # info
                color = self.colors['primary']
            
            # Durum etiketini güncelle
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.config(text=message, fg=color)
                
                # Status frame'i göster
                if hasattr(self, 'status_frame'):
                    self.status_frame.pack(fill=tk.X, pady=(15, 0))
            
            # 🔧 Lambda scope düzeltmesi - değişkeni yakala
            def clear_status_safe():
                """Güvenli status temizleme"""
                try:
                    if (hasattr(self, 'status_label') and 
                        self.status_label and 
                        self.status_label.winfo_exists()):
                        self.status_label.config(text="")
                except Exception as e:
                    logging.warning(f"Status temizleme hatası: {e}")
            
            # Otomatik temizlik zamanlayıcısı - düzeltilmiş
            if hasattr(self, 'status_timer_id') and self.status_timer_id:
                try:
                    self.after_cancel(self.status_timer_id)
                except Exception:
                    pass
            
            self.status_timer_id = self.after(5000, clear_status_safe)
            
        except Exception as e:
            logging.error(f"Status gösterim hatası: {e}")

    def _clear_status(self):
        """Durum mesajını temizler - güvenli versiyon"""
        try:
            if (hasattr(self, 'status_label') and 
                self.status_label and 
                self.status_label.winfo_exists()):
                self.status_label.config(text="")
        except Exception as e:
            logging.warning(f"Status temizleme hatası: {e}")
    


    def _show_progress(self, show=True, message=None):
        """İlerleme çubuğunu gösterir/gizler"""
        if show:
            # İlerleme çubuğunu göster
            self.status_frame.pack(fill=tk.X, pady=(15, 0))
            self.progress_bar.start(10)
            
            # Mesaj varsa göster
            if message:
                self.status_label.config(text=message, fg=self.colors['primary'])
        else:
            # İlerleme çubuğunu durdur
            self.progress_bar.stop()
            
            # Mesaj yoksa gizle
            if not self.status_label.cget('text'):
                self.status_frame.pack_forget()
    
    def _validate_email(self, email):
        """E-posta adresini doğrular"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None
    
    def packContent(self):
        """İçeriği paketler (geriye dönük uyumluluk)"""
        self.pack(fill=tk.BOTH, expand=True)
    
    def destroy(self):
        """Widget'ı yok eder - gelişmiş temizlik"""
        try:
            # Timer'ları temizle
            if hasattr(self, 'status_timer_id') and self.status_timer_id:
                try:
                    self.after_cancel(self.status_timer_id)
                except Exception:
                    pass
            
            # Animasyonları durdur
            if hasattr(self, 'anim_ids'):
                for anim_id in self.anim_ids:
                    try:
                        self.after_cancel(anim_id)
                    except Exception:
                        pass
            
            # Google login durumunu sıfırla
            self.google_login_in_progress = False
            
            # Widget'ı yok et
            super().destroy()
            
        except Exception as e:
            logging.error(f"Login destroy hatası: {e}")