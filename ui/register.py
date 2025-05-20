import tkinter as tk
from tkinter import ttk, messagebox
import logging
import threading
import os
import math
import time
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import re
import random

class RegisterFrame(tk.Frame):
    """Modern, şık ve güven veren kayıt ekranı."""

    def __init__(self, parent, auth, on_register_success, on_back_to_login):
        super().__init__(parent, bg="#FFFFFF")
        self.parent = parent
        self.auth = auth
        self.on_register_success = on_register_success
        self.on_back_to_login = on_back_to_login
        
        # Değişkenleri başlangıçta tanımla
        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.confirm_var = tk.StringVar()
        self.terms_var = tk.BooleanVar(value=False)
        
        # Animasyon değişkenleri
        self.anim_ids = []
        self.bubble_particles = []
        
        # Renk paleti - tatlı mor tonları
        self.colors = {
            'primary': "#AB47BC",       # Ana mor
            'primary_dark': "#7B1FA2",  # Koyu mor
            'primary_light': "#CE93D8", # Açık mor
            'secondary': "#F06292",     # Pembe vurgu rengi
            'success': "#A5D6A7",       # Yeşil
            'danger': "#F44336",        # Kırmızı
            'warning': "#FF9800",       # Turuncu
            'light_bg': "#F5F5F5",      # Açık arka plan
            'card_bg': "#FFFFFF",       # Kart arka planı
            'text': "#4A4A4A",          # Koyu metin
            'text_secondary': "#757575",# İkincil metin
            'border': "#E0E0E0",        # Çerçeve rengi
            'bg_gradient1': "#D1C4E9",  # Gradient başlangıç rengi (pastel mor)
            'bg_gradient2': "#F8BBD0",  # Gradient orta rengi (pastel pembe)
            'bg_gradient3': "#BBDEFB",  # Gradient bitiş rengi (açık mavi)
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
        
        # Sol panel - animasyonlu arka plan ve marka mesajı
        self.left_panel = tk.Frame(self.main_frame, bg=self.colors['light_bg'], width=600)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Animasyonlu arka plan için canvas
        self.bg_canvas = tk.Canvas(self.left_panel, highlightthickness=0)
        self.bg_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Arka plan gradienti çiz
        self._draw_background(self.bg_canvas)
        
        # Marka mesajı çerçevesi - Canvas üzerinde
        self.brand_frame = tk.Frame(self.bg_canvas, bg=self.colors['light_bg'])
        
        # Logo
        self._create_logo(self.brand_frame)
        
        # Marka sloganı
        self._create_slogan(self.brand_frame)
        
        # Güvenlik özellikleri
        self._create_security_features(self.brand_frame)
        
        # Canvas üzerinde brand_frame için pencere oluştur
        self.brand_window = self.bg_canvas.create_window(50, 50, 
                                                        anchor=tk.NW, 
                                                        window=self.brand_frame)
        
        # Sağ panel - kayıt formu
        self.right_panel = tk.Frame(self.main_frame, bg=self.colors['card_bg'], padx=40, pady=30)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)
        
        # Kayıt formu
        self._create_register_form()
    
    def _draw_background(self, canvas):
        """Gradient arka planı ve efektleri çizer"""
        width = self.winfo_width() or 800
        height = self.winfo_height() or 600
        
        # Canvas'ı temizle
        canvas.delete("background")
        
        # Gradient arkaplan
        gradient_colors = [self.colors['bg_gradient1'], self.colors['bg_gradient2'], self.colors['bg_gradient3']]
        for i in range(height):
            percent = i / height
            if percent < 0.5:
                t = percent * 2
                r1, g1, b1 = self._hex_to_rgb(gradient_colors[0])
                r2, g2, b2 = self._hex_to_rgb(gradient_colors[1])
            else:
                t = (percent - 0.5) * 2
                r1, g1, b1 = self._hex_to_rgb(gradient_colors[1])
                r2, g2, b2 = self._hex_to_rgb(gradient_colors[2])
            
            r = int(r1 * (1 - t) + r2 * t)
            g = int(g1 * (1 - t) + g2 * t)
            b = int(b1 * (1 - t) + b2 * t)
            
            color = f'#{r:02x}{g:02x}{b:02x}'
            canvas.create_line(0, i, width, i, fill=color, tags="background")
        
        # Dekoratif daireler
        canvas.create_oval(width-250, height-250, width+100, height+100, 
                         fill=self.colors['primary_light'], outline="", 
                         tags="background")
        canvas.create_oval(-50, -50, 150, 150, 
                         fill="#E1BEE7", outline="", 
                         tags="background")
        canvas.create_oval(width-200, height//2-100, width-50, height//2+100, 
                         fill="#F3E5F5", outline="", 
                         tags="background")
    
    def _create_logo(self, parent):
        """Logo alanını oluşturur"""
        logo_frame = tk.Frame(parent, bg=self.colors['light_bg'], padx=30, pady=20)
        logo_frame.pack(anchor=tk.W)
        
        # Logo yükleme
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    "resources", "icons", "logo.png")
            
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                img = img.resize((80, 80), Image.LANCZOS)
                
                # Parlaklık ayarı
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.2)
                
                self.logo_image = ImageTk.PhotoImage(img)
                
                logo_label = tk.Label(logo_frame, image=self.logo_image, bg=self.colors['light_bg'])
                logo_label.pack(side=tk.LEFT)
                
                # Logo adı
                logo_text = tk.Label(logo_frame, text="Guard", 
                                   font=("Roboto", 30, "bold"), 
                                   fg=self.colors['primary'], 
                                   bg=self.colors['light_bg'])
                logo_text.pack(side=tk.LEFT, padx=(15, 0))
            else:
                # Logo yok - metin logo
                logo_text = tk.Label(logo_frame, text="G", 
                                font=("Roboto", 40, "bold"), 
                                fg=self.colors['primary'], 
                                bg=self.colors['light_bg'])
                logo_text.pack(side=tk.LEFT)
                
                logo_name = tk.Label(logo_frame, text="Guard", 
                                font=("Roboto", 30, "bold"), 
                                fg=self.colors['primary'], 
                                bg=self.colors['light_bg'])
                logo_name.pack(side=tk.LEFT, padx=(15, 0))
        except Exception as e:
            logging.warning(f"Logo yüklenemedi: {str(e)}")
            # Fallback - metin logo
            logo_text = tk.Label(logo_frame, text="G", 
                               font=("Roboto", 40, "bold"), 
                               fg=self.colors['primary'], 
                               bg=self.colors['light_bg'])
            logo_text.pack(side=tk.LEFT)
            
            logo_name = tk.Label(logo_frame, text="Guard", 
                               font=("Roboto", 30, "bold"), 
                               fg=self.colors['primary'], 
                               bg=self.colors['light_bg'])
            logo_name.pack(side=tk.LEFT, padx=(15, 0))
    
    def _create_slogan(self, parent):
        """Marka sloganı alanını oluşturur"""
        slogan_frame = tk.Frame(parent, bg=self.colors['light_bg'], padx=30, pady=20)
        slogan_frame.pack(anchor=tk.W, fill=tk.X)
        
        main_slogan = tk.Label(slogan_frame, 
                             text="Guard ile\nGüvendesiniz", 
                             font=("Roboto", 34, "bold"), 
                             fg=self.colors['primary'], 
                             bg=self.colors['light_bg'],
                             justify=tk.LEFT)
        main_slogan.pack(anchor=tk.W)
        
        sub_slogan = tk.Label(slogan_frame, 
                            text="Hızlı ve güvenli bir şekilde hesabınızı oluşturun.", 
                            font=("Roboto", 14), 
                            fg=self.colors['text_secondary'], 
                            bg=self.colors['light_bg'],
                            justify=tk.LEFT,
                            wraplength=450)
        sub_slogan.pack(anchor=tk.W, pady=20)
    
    def _create_security_features(self, parent):
        """Güvenlik özellikleri listeleme alanını oluşturur"""
        features_frame = tk.Frame(parent, bg=self.colors['light_bg'], padx=30, pady=20)
        features_frame.pack(anchor=tk.W, fill=tk.X)
        
        # Başlık
        features_title = tk.Label(features_frame, 
                                text="Neden Guard?", 
                                font=("Roboto", 16, "bold"), 
                                fg=self.colors['primary'], 
                                bg=self.colors['light_bg'])
        features_title.pack(anchor=tk.W, pady=(0, 15))
        
        # Güvenlik özellikleri (Her biri ikon + metin)
        security_features = [
            ("🔒", "Uçtan uca şifreleme"),
            ("🛡️", "Gelişmiş düşme algılama"),
            ("📱", "Çoklu cihaz desteği"),
            ("🔔", "Gerçek zamanlı bildirimler")
        ]
        
        for icon, text in security_features:
            feature_frame = tk.Frame(features_frame, bg=self.colors['light_bg'])
            feature_frame.pack(anchor=tk.W, pady=5, fill=tk.X)
            
            # İkon
            feature_icon = tk.Label(feature_frame, 
                                  text=icon, 
                                  font=("Roboto", 20), 
                                  fg=self.colors['secondary'], 
                                  bg=self.colors['light_bg'])
            feature_icon.pack(side=tk.LEFT, padx=(0, 10))
            
            # Metin
            feature_text = tk.Label(feature_frame, 
                                  text=text, 
                                  font=("Roboto", 14), 
                                  fg=self.colors['text'], 
                                  bg=self.colors['light_bg'])
            feature_text.pack(side=tk.LEFT)
    
    def _create_register_form(self):
        """Kayıt formunu oluşturur"""
        # Form başlığı
        header_frame = tk.Frame(self.right_panel, bg=self.colors['card_bg'])
        header_frame.pack(fill=tk.X, pady=(0, 25))
        
        title_label = tk.Label(header_frame, 
                             text="Hesap Oluştur", 
                             font=("Roboto", 26, "bold"), 
                             fg=self.colors['primary'], 
                             bg=self.colors['card_bg'])
        title_label.pack(anchor=tk.W)
        
        subtitle_label = tk.Label(header_frame, 
                                text="Hızlı ve güvenli bir şekilde kaydolun", 
                                font=("Roboto", 14), 
                                fg=self.colors['text_secondary'], 
                                bg=self.colors['card_bg'])
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Form alanları
        form_frame = tk.Frame(self.right_panel, bg=self.colors['card_bg'])
        form_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Ad Soyad alanı
        self._create_input_field(form_frame, "Ad Soyad", "👤", self.name_var)
        
        # Telefon alanı (isteğe bağlı)
        self._create_input_field(form_frame, "Telefon (İsteğe Bağlı)", "📱", self.phone_var)
        
        # E-posta alanı
        self._create_input_field(form_frame, "E-posta", "📧", self.email_var)
        
        # Şifre alanı
        self._create_input_field(form_frame, "Şifre", "🔒", self.password_var, show_password=True)
        
        # Şifre (Tekrar) alanı
        self._create_input_field(form_frame, "Şifre (Tekrar)", "🔒", self.confirm_var, show_password=True)
        
        # Kullanım koşulları onayı
        terms_frame = tk.Frame(form_frame, bg=self.colors['card_bg'], pady=15)
        terms_frame.pack(fill=tk.X)
        
        terms_check = tk.Checkbutton(terms_frame, 
                                   text="Kullanım koşullarını ve gizlilik politikasını kabul ediyorum", 
                                   font=("Roboto", 12), 
                                   fg=self.colors['text'], 
                                   bg=self.colors['card_bg'],
                                   activebackground=self.colors['card_bg'],
                                   variable=self.terms_var,
                                   cursor="hand2")
        terms_check.pack(anchor=tk.W)
        
        # Kayıt ol butonu - geniş ve belirgin
        button_frame = tk.Frame(form_frame, bg=self.colors['card_bg'], pady=10)
        button_frame.pack(fill=tk.X)
        
        register_button = tk.Button(button_frame, 
                                  text="Hesap Oluştur", 
                                  font=("Roboto", 14, "bold"), 
                                  fg="#FFFFFF", 
                                  bg=self.colors['primary'],
                                  activebackground=self.colors['primary_dark'],
                                  activeforeground="#FFFFFF",
                                  relief="flat", 
                                  bd=0, 
                                  padx=15, 
                                  pady=12,
                                  command=self._on_submit,
                                  cursor="hand2")
        register_button.pack(fill=tk.X)
        
        # Hover efekti
        register_button.bind("<Enter>", lambda e: register_button.config(bg=self.colors['primary_dark']))
        register_button.bind("<Leave>", lambda e: register_button.config(bg=self.colors['primary']))
        
        # Ayırıcı
        divider_frame = tk.Frame(form_frame, bg=self.colors['card_bg'], pady=15)
        divider_frame.pack(fill=tk.X)
        
        divider_left = tk.Frame(divider_frame, height=1, bg=self.colors['border'])
        divider_left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        divider_text = tk.Label(divider_frame, 
                              text="veya", 
                              font=("Roboto", 12), 
                              fg=self.colors['text_secondary'], 
                              bg=self.colors['card_bg'])
        divider_text.pack(side=tk.LEFT)
        
        divider_right = tk.Frame(divider_frame, height=1, bg=self.colors['border'])
        divider_right.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Google ile kayıt butonu
        google_button = tk.Button(form_frame, 
                                text="Google ile Kayıt Ol", 
                                font=("Roboto", 14), 
                                fg=self.colors['text'], 
                                bg=self.colors['light_bg'],
                                activebackground="#E0E0E0",
                                activeforeground=self.colors['text'],
                                relief="flat", 
                                bd=0, 
                                padx=15, 
                                pady=12,
                                command=self._google_register,
                                cursor="hand2")
        google_button.pack(fill=tk.X, pady=5)
        
        # Google ikonu eklemeye çalış
        try:
            google_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                           "resources", "icons", "google_icon.png")
            
            if os.path.exists(google_icon_path):
                google_img = Image.open(google_icon_path).resize((20, 20), Image.LANCZOS)
                self.google_icon = ImageTk.PhotoImage(google_img)
                
                # İkonu ekle
                google_button.config(image=self.google_icon, compound=tk.LEFT, padx=15)
        except Exception as e:
            logging.warning(f"Google ikonu yüklenemedi: {str(e)}")
        
        # Zaten hesabınız var mı? bağlantısı
        login_frame = tk.Frame(form_frame, bg=self.colors['card_bg'], pady=15)
        login_frame.pack(fill=tk.X)
        
        login_text = tk.Label(login_frame, 
                            text="Zaten hesabınız var mı? ", 
                            font=("Roboto", 12), 
                            fg=self.colors['text'], 
                            bg=self.colors['card_bg'])
        login_text.pack(side=tk.LEFT)
        
        login_link = tk.Label(login_frame, 
                            text="Giriş Yap", 
                            font=("Roboto", 12, "bold", "underline"), 
                            fg=self.colors['primary'], 
                            bg=self.colors['card_bg'],
                            cursor="hand2")
        login_link.pack(side=tk.LEFT)
        login_link.bind("<Button-1>", self._back_to_login_click)
        
        # Hover efekti
        login_link.bind("<Enter>", lambda e: login_link.config(fg=self.colors['primary_dark']))
        login_link.bind("<Leave>", lambda e: login_link.config(fg=self.colors['primary']))
        
        # İlerleme çubuğu ve durum mesajı
        self.status_frame = tk.Frame(self.right_panel, bg=self.colors['card_bg'])
        
        # İlerleme çubuğu
        style = ttk.Style()
        style.configure("Register.Horizontal.TProgressbar", 
                      troughcolor=self.colors['light_bg'],
                      background=self.colors['primary'])
        
        self.progress_bar = ttk.Progressbar(self.status_frame, 
                                          style="Register.Horizontal.TProgressbar", 
                                          mode="indeterminate", 
                                          length=100)
        self.progress_bar.pack(fill=tk.X)
        
        # Durum mesajı
        self.status_label = tk.Label(self.status_frame, 
                                   text="", 
                                   font=("Roboto", 11), 
                                   fg=self.colors['primary'], 
                                   bg=self.colors['card_bg'])
        self.status_label.pack(pady=5)
        
        # Başlangıçta gizle
        self.status_frame.pack_forget()
    
    def _create_input_field(self, parent, label_text, icon_text, var, show_password=False):
        """Giriş alanı oluşturur"""
        # Ana çerçeve
        field_frame = tk.Frame(parent, bg=self.colors['card_bg'], pady=10)
        field_frame.pack(fill=tk.X)
        
        # Etiket
        label = tk.Label(field_frame, 
                       text=label_text, 
                       font=("Roboto", 12, "bold"), 
                       fg=self.colors['text'], 
                       bg=self.colors['card_bg'])
        label.pack(anchor=tk.W, pady=(0, 8))
        
        # Giriş alanı çerçevesi - yuvarlak kenarlıklı
        input_frame = tk.Frame(field_frame, 
                             bg=self.colors['card_bg'], 
                             highlightbackground=self.colors['border'],
                             highlightthickness=1,
                             bd=0)
        input_frame.pack(fill=tk.X)
        
        # İkon çerçevesi
        icon_frame = tk.Frame(input_frame, bg=self.colors['card_bg'], padx=12, pady=10)
        icon_frame.pack(side=tk.LEFT)
        
        # İkon
        icon = tk.Label(icon_frame, 
                      text=icon_text, 
                      font=("Roboto", 14), 
                      fg=self.colors['text_secondary'], 
                      bg=self.colors['card_bg'])
        icon.pack()
        
        # Giriş alanı
        show_char = "•" if show_password else ""
        entry = tk.Entry(input_frame, 
                       textvariable=var,
                       font=("Roboto", 14), 
                       fg=self.colors['text'], 
                       bg=self.colors['card_bg'],
                       relief="flat", 
                       bd=0, 
                       highlightthickness=0,
                       show=show_char)
        entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        # Şifre göster/gizle butonu (sadece şifre alanları için)
        if show_password:
            self.show_password_var = tk.BooleanVar(value=False)
            
            def toggle_password():
                current = self.show_password_var.get()
                self.show_password_var.set(not current)
                entry.config(show="" if self.show_password_var.get() else "•")
                toggle_btn.config(text="👁️" if self.show_password_var.get() else "👁️‍🗨️")
            
            toggle_btn = tk.Label(input_frame, 
                                text="👁️‍🗨️", 
                                font=("Roboto", 14), 
                                fg=self.colors['text_secondary'], 
                                bg=self.colors['card_bg'],
                                cursor="hand2")
            toggle_btn.pack(side=tk.RIGHT, padx=12, pady=10)
            toggle_btn.bind("<Button-1>", lambda e: toggle_password())
        
        # Odak durumunda kenar rengini değiştir
        entry.bind("<FocusIn>", lambda e: input_frame.config(highlightbackground=self.colors['primary']))
        entry.bind("<FocusOut>", lambda e: self._validate_on_focusout(entry, input_frame, label_text.lower()))
        
        return entry
    
    def _validate_on_focusout(self, entry, frame, field_type):
        """Alan odak dışına çıktığında doğrulama yapar"""
        value = entry.get().strip()
        
        if "e-posta" in field_type:
            # E-posta doğrulama
            if value and not self._validate_email(value):
                frame.config(highlightbackground=self.colors['danger'])
                entry.config(fg=self.colors['danger'])
                self._show_status("Geçerli bir e-posta adresi giriniz", "error")
                return False
        elif "şifre (tekrar)" in field_type:
            # Şifre tekrar doğrulama
            if value and value != self.password_var.get():
                frame.config(highlightbackground=self.colors['danger'])
                entry.config(fg=self.colors['danger'])
                self._show_status("Şifreler eşleşmiyor", "error")
                return False
        elif "şifre" in field_type:
            # Şifre uzunluk kontrolü
            if value and len(value) < 6:
                frame.config(highlightbackground=self.colors['danger'])
                entry.config(fg=self.colors['danger'])
                self._show_status("Şifre en az 6 karakter olmalıdır", "error")
                return False
        elif "ad soyad" in field_type:
            # Ad soyad boş kontrolü
            if not value:
                frame.config(highlightbackground=self.colors['danger'])
                entry.config(fg=self.colors['danger'])
                self._show_status("Ad Soyad alanı boş olamaz", "error")
                return False
        
        # Doğrulama başarılı - normal renge dön
        frame.config(highlightbackground=self.colors['border'])
        entry.config(fg=self.colors['text'])
        self._clear_status()
        return True
    
    def _create_floating_bubbles(self):
        """Kayan baloncukları oluşturur"""
        width = self.bg_canvas.winfo_width() or 600
        height = self.bg_canvas.winfo_height() or 800
        
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
            width = self.bg_canvas.winfo_width()
            height = self.bg_canvas.winfo_height()
            
            if width > 1 and height > 1:  # Geçerli boyutlar
                # Canvas'ı temizle
                self.bg_canvas.delete("bubble")
                
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
                    self.bg_canvas.create_oval(
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
        """Ekran boyutu değiştiğinde çağrılır"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width > 100 and height > 100:  # Geçerli boyutlar
            # Arka planı yeniden çiz
            self._draw_background(self.bg_canvas)
            
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
                    self.bg_canvas.coords(self.brand_window, 50, height / 2 - brand_height / 2)
                
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
                    self.bg_canvas.coords(self.brand_window, 30, height / 2 - brand_height / 2)
                
            else:  # Dar ekran - sadece form göster
                # Sol paneli gizle
                if self.left_panel.winfo_ismapped():
                    self.left_panel.pack_forget()
                self.right_panel.config(width=width)
            
            # Kayan baloncukları yeniden oluştur
            if len(self.bubble_particles) > 0:
                self.bubble_particles.clear()
                self._create_floating_bubbles()
    
    def _on_submit(self):
        """Kayıt ol butonuna tıklandığında çağrılır"""
        # Form verilerini al
        name = self.name_var.get().strip()
        email = self.email_var.get().strip()
        password = self.password_var.get()
        confirm = self.confirm_var.get()
        
        # Zorunlu alanları kontrol et
        if not name:
            self._show_status("Ad Soyad alanını doldurunuz", "error")
            return
        
        if not email:
            self._show_status("E-posta adresinizi giriniz", "error")
            return
        
        if not password:
            self._show_status("Şifrenizi giriniz", "error")
            return
        
        if not confirm:
            self._show_status("Şifre tekrarını giriniz", "error")
            return
        
        # Format kontrolü
        if not self._validate_email(email):
            self._show_status("Geçerli bir e-posta adresi giriniz", "error")
            return
        
        # Şifre uzunluğu
        if len(password) < 6:
            self._show_status("Şifre en az 6 karakter olmalıdır", "error")
            return
        
        # Şifre eşleşmesi
        if password != confirm:
            self._show_status("Şifreler eşleşmiyor", "error")
            return
        
        # Kullanım koşullarını kabul etme
        if not self.terms_var.get():
            self._show_status("Kullanım koşullarını kabul etmelisiniz", "warning")
            return
        
        # İlerleme çubuğunu göster
        self._show_progress(True, "Hesap oluşturuluyor...")
        
        # Kayıt işlemini başlat
        threading.Thread(target=self._sign_up_process, 
                         args=(email, password, name), 
                         daemon=True).start()
    
    def _sign_up_process(self, email, password, name):
        """Kayıt işlemini gerçekleştirir"""
        try:
            # Firebase ile kullanıcı oluştur
            user = self.auth.create_user_with_email_password(email, password)
            
            # Profil güncelle - isim ekle
            self.auth.update_profile(display_name=name)
            
            # Telefon varsa ekle
            phone = self.phone_var.get().strip()
            if phone:
                self.auth.update_profile(phone_number=phone)
            
            # Kısa bir gecikme ekle (animasyon için)
            time.sleep(0.8)
            
            # Kayıt başarılıysa
            self.after(0, lambda: self._handle_register_success(user))
            
        except Exception as e:
            error_msg = str(e)
            
            # Kullanıcı dostu hata mesajları
            if "EMAIL_EXISTS" in error_msg:
                error_msg = "Bu e-posta adresi zaten kullanımda"
            elif "WEAK_PASSWORD" in error_msg:
                error_msg = "Şifre çok zayıf. Daha güçlü bir şifre giriniz"
            elif "INVALID_EMAIL" in error_msg:
                error_msg = "Geçersiz e-posta formatı"
            
            self.after(0, lambda: self._show_status(error_msg, "error"))
            self.after(0, lambda: self._show_progress(False))
    
    def _google_register(self):
        """Google ile kayıt"""
        self._show_progress(True, "Google ile bağlanılıyor...")
        
        threading.Thread(target=self._google_register_process, 
                         daemon=True).start()
    
    def _google_register_process(self):
        """Google kayıt işlemini gerçekleştirir"""
        try:
            # Google ile kimlik doğrulama
            auth_url, auth_code = self.auth.sign_in_with_google()
            
            # Kullanıcı yanıtını bekle
            self.after(0, lambda: self._complete_google_register(auth_code))
            
        except Exception as e:
            error_msg = f"Google bağlantısı kurulamadı: {str(e)}"
            self.after(0, lambda: self._show_status(error_msg, "error"))
            self.after(0, lambda: self._show_progress(False))
    
    def _complete_google_register(self, auth_code):
        """Google kimlik doğrulama sonrası kayıt tamamlama"""
        if not auth_code:
            self._show_status("Google kayıt işlemi iptal edildi", "info")
            self._show_progress(False)
            return
        
        try:
            # Google kimlik doğrulama tamamla
            user = self.auth.complete_google_sign_in(None, auth_code)
            
            # Telefon numarası ekle (eğer girilmişse)
            phone = self.phone_var.get().strip()
            if phone:
                self.auth.update_profile(phone_number=phone)
            
            # Kayıt başarılıysa
            self._handle_register_success(user)
            
        except Exception as e:
            error_msg = f"Google kayıt tamamlanamadı: {str(e)}"
            self._show_status(error_msg, "error")
            self._show_progress(False)
    
    def _handle_register_success(self, user):
        """Kayıt başarılı olduğunda çağrılır"""
        logging.info(f"Yeni kullanıcı kaydedildi: {user.get('email', '')}")
        
        # İlerleme durumunu güncelle
        self._show_status("Hesap başarıyla oluşturuldu!", "success")
        
        # Başarı animasyonunu göster
        self._show_success_animation(user)
        
        # Callback'i çağır (varsa)
        if self.on_register_success:
            # on_register_success metoduna user parametresi yerine, doğrudan dashboard'a geçiş yapmasını sağlayacağız
            self.after(1500, lambda: self.on_register_success(user))
    
    def _back_to_login_click(self, event=None):
        """Giriş ekranına dön bağlantısına tıklandığında"""
        if self.on_back_to_login:
            self.on_back_to_login()
    
    def _show_success_animation(self, user):
        """Başarılı kayıt animasyonu gösterir"""
        # Form içeriğini temizle
        for widget in self.right_panel.winfo_children():
            widget.destroy()
        
        # Başarı çerçevesi
        success_frame = tk.Frame(self.right_panel, bg=self.colors['card_bg'], padx=40, pady=40)
        success_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tik işareti animasyonu için canvas
        check_canvas = tk.Canvas(success_frame, width=150, height=150, 
                               bg=self.colors['card_bg'], highlightthickness=0)
        check_canvas.pack(pady=(20, 30))
        
        # Animasyonu çiz
        self._animate_success_checkmark(check_canvas)
        
        # Başarı mesajı
        success_title = tk.Label(success_frame, 
                               text="Hesap Oluşturuldu!", 
                               font=("Roboto", 26, "bold"), 
                               fg=self.colors['success'], 
                               bg=self.colors['card_bg'])
        success_title.pack(pady=(0, 20))
        
        # Kullanıcı bilgisi
        welcome_text = tk.Label(success_frame, 
                              text=f"Hoş geldiniz, {user.get('displayName', 'Kullanıcı')}!", 
                              font=("Roboto", 16), 
                              fg=self.colors['text'], 
                              bg=self.colors['card_bg'])
        welcome_text.pack(pady=(0, 30))
        
        # Giriş yap butonu
        login_button = tk.Button(success_frame, 
                               text="Giriş Yap", 
                               font=("Roboto", 14, "bold"), 
                               fg="#FFFFFF", 
                               bg=self.colors['primary'],
                               activebackground=self.colors['primary_dark'],
                               activeforeground="#FFFFFF",
                               relief="flat", 
                               padx=30, 
                               pady=12,
                               cursor="hand2",
                               command=self._back_to_login_click)
        login_button.pack(pady=(20, 0))
    
    def _animate_success_checkmark(self, canvas):
        """Başarı için tik işareti animasyonu"""
        # Daire için koordinatlar
        center_x, center_y = 75, 75
        radius = 50
        
        # Daire çiz - animasyonlu
        def animate_circle(angle=0, max_angle=360):
            if angle <= max_angle:
                # Daire parçasını çiz
                canvas.delete("circle_arc")
                canvas.create_arc(
                    center_x - radius, center_y - radius,
                    center_x + radius, center_y + radius,
                    start=0, extent=angle,
                    style=tk.ARC, width=5,
                    outline=self.colors['success'],
                    tags="circle_arc"
                )
                
                # Sonraki adımı planla
                anim_id = canvas.after(5, lambda: animate_circle(angle + 6, max_angle))
                self.anim_ids.append(anim_id)
            else:
                # Daire tamamlandı, tik işaretini çiz
                animate_tick()
        
        # Tik işareti için koordinatlar
        tick_points = [
            (45, 75),   # Sol nokta
            (65, 95),   # Orta nokta
            (105, 55)   # Sağ üst nokta
        ]
        
        # Tik işareti animasyonu
        def animate_tick(step=0, max_step=30):
            if step <= max_step:
                # İlerleme
                progress = step / max_step
                
                if progress <= 0.5:  # İlk çizgi (sol-orta)
                    p = progress * 2
                    x1, y1 = tick_points[0]
                    x2 = tick_points[0][0] + (tick_points[1][0] - tick_points[0][0]) * p
                    y2 = tick_points[0][1] + (tick_points[1][1] - tick_points[0][1]) * p
                    
                    # İlk çizgi
                    canvas.delete("tick_line")
                    canvas.create_line(
                        x1, y1, x2, y2,
                        width=5, fill=self.colors['success'],
                        capstyle=tk.ROUND, tags="tick_line"
                    )
                else:  # İkinci çizgi (orta-sağ üst)
                    p = (progress - 0.5) * 2
                    x1, y1 = tick_points[1]
                    x2 = tick_points[1][0] + (tick_points[2][0] - tick_points[1][0]) * p
                    y2 = tick_points[1][1] + (tick_points[2][1] - tick_points[1][1]) * p
                    
                    # Tam ilk çizgi
                    canvas.delete("tick_line")
                    canvas.create_line(
                        tick_points[0][0], tick_points[0][1],
                        tick_points[1][0], tick_points[1][1],
                        width=5, fill=self.colors['success'],
                        capstyle=tk.ROUND, tags="tick_line"
                    )
                    
                    # İkinci çizgi (büyüyen)
                    canvas.create_line(
                        x1, y1, x2, y2,
                        width=5, fill=self.colors['success'],
                        capstyle=tk.ROUND, tags="tick_line"
                    )
                
                # Sonraki adımı planla
                anim_id = canvas.after(10, lambda: animate_tick(step + 1, max_step))
                self.anim_ids.append(anim_id)
        
        # Animasyonu başlat
        animate_circle()
    
    def _show_status(self, message, status_type="info"):
        """Durum mesajını gösterir"""
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
        self.status_label.config(text=message, fg=color)
        
        # Status frame'i göster
        self.status_frame.pack(fill=tk.X, pady=(15, 0))
        
        # Otomatik temizlik zamanlayıcısı
        if hasattr(self, 'status_timer_id'):
            self.after_cancel(self.status_timer_id)
        
        self.status_timer_id = self.after(5000, lambda: self._clear_status())
    
    def _clear_status(self):
        """Durum mesajını temizler"""
        if hasattr(self, 'status_label') and self.status_label.winfo_exists():
            self.status_label.config(text="")
    
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
    
    def _hex_to_rgb(self, hex_color):
        """Hex renk kodunu RGB değerlerine dönüştürür"""
        hex_color = hex_color.lstrip('#')
        return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    
    def packContent(self):
        """İçeriği paketler (geriye dönük uyumluluk)"""
        self.pack(fill=tk.BOTH, expand=True)
    
    def destroy(self):
        """Widget'ı yok eder ve tüm animasyonları durdurur"""
        # Animasyonları durdur
        for anim_id in self.anim_ids:
            try:
                self.after_cancel(anim_id)
            except Exception:
                pass
        
        # Status timer'ı durdur
        if hasattr(self, 'status_timer_id'):
            self.after_cancel(self.status_timer_id)
        
        # Temizlik
        super().destroy()