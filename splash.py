# =======================================================================================
# 📄 Dosya Adı: SplashScreen.py
# 📁 Konum: guard_pc_app/ui/SplashScreen.py
# 📌 Açıklama:
# Ultra modern Guard AI splash screen - YOLOv11 Pose Estimation entegrasyonu.
# Gelişmiş animasyonlar ve gerçekçi yükleme simülasyonu.
# 🔗 Bağlantılı Dosyalar:
# - Yok (Bağımsız splash ekranı)
# =======================================================================================

import tkinter as tk
import time
import threading
import os
import logging
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import math
import random

class SplashScreen:
    """
    Ultra modern Guard AI splash screen - YOLOv11 Pose Estimation entegrasyonu.
    Gelişmiş animasyonlar ve gerçekçi yükleme simülasyonu.
    """
    
    def __init__(self, root, duration=10, app_info=None):
        """
        Args:
            root (tk.Tk): Ana pencere
            duration (float): Açılış ekranı süresi (saniye)
            app_info (dict): Uygulama bilgileri (versiyon, özellikler, vs.)
        """
        # Ana pencereyi başlat
        self.root = root  # Tkinter root
        self.duration = duration  # Süre
        self.app_info = app_info or {}  # Uygulama bilgileri
        self.splash_window = None  # Splash penceresi
        self.particles = []  # Parçacıklar
        self.initialization_steps = []  # Başlatma adımları
        self.current_step = 0  # Mevcut adım
        
        # Ana pencereyi gizle
        self.root.withdraw()  # Pencereyi gizle
        
        # Uygulama bilgilerini işle
        self._process_app_info()  # Bilgileri hazırla
        
        # Başlatma adımlarını tanımla
        self._setup_initialization_steps()  # Adımları ayarla
        
        # Splash ekranını göster
        self._show_splash()  # Ekranı oluştur
        
        # Gerçekçi yükleme simülasyonu başlat
        self._start_initialization_simulation()  # Simülasyonu başlat
        
        # Belirli bir süre sonra ana pencereyi göster
        self.root.after(int(self.duration * 1000), self._close_splash)  # Kapatma zamanlayıcısı

    def _process_app_info(self):
        """Uygulama bilgilerini işle ve varsayılanları ayarla."""
        # Varsayılan değerler
        default_info = {
            'name': 'GUARD AI',  # Uygulama adı
            'version': '2.0.0',  # Versiyon
            'description': 'YOLOv11 Pose Estimation | Akıllı Düşme Algılama',  # Açıklama
            'author': 'mehmetkaratslar',  # Yazar
            'year': '2025',  # Yıl
            'features': [  # Özellikler
                'YOLOv11 Pose Estimation',
                'DeepSORT Multi-Object Tracking',
                'Real-time Fall Detection',
                'Firebase Cloud Integration',
                'Advanced Analytics',
                'Multi-Camera Support'
            ],
            'tech_stack': [  # Teknoloji yığını
                'Real-time AI Detection',
                'DeepSORT Tracking', 
                'Firebase Cloud'
            ],
            'loading_steps': [  # Yükleme adımları
                {'text': 'Guard AI sistemi başlatılıyor...', 'duration': 0.8, 'progress': 10},
                {'text': 'YOLOv11 Pose modeli yükleniyor...', 'duration': 1.2, 'progress': 25},
                {'text': 'DeepSORT tracker başlatılıyor...', 'duration': 0.7, 'progress': 40},
                {'text': 'Kamera sistemleri kontrol ediliyor...', 'duration': 0.9, 'progress': 55},
                {'text': 'Düşme algılama algoritması hazırlanıyor...', 'duration': 0.8, 'progress': 70},
                {'text': 'Firebase bağlantısı kuruluyor...', 'duration': 0.6, 'progress': 80},
                {'text': 'Bildirim sistemi yapılandırılıyor...', 'duration': 0.5, 'progress': 90},
                {'text': 'Son kontroller yapılıyor...', 'duration': 0.4, 'progress': 95},
                {'text': 'Guard AI hazır! Giriş ekranına yönlendiriliyor...', 'duration': 0.5, 'progress': 100}
            ]
        }
        
        # App info ile varsayılanları birleştir
        for key, value in default_info.items():
            if key not in self.app_info:
                self.app_info[key] = value  # Varsayılan ekle

    def _setup_initialization_steps(self):
        """Başlatma adımlarını app_info'dan al."""
        self.initialization_steps = self.app_info.get('loading_steps', [])  # Adımları al
    
    def _show_splash(self):
        """ modern ve etkileyici Guard AI splash ekranı."""
        # Yeni bir pencere oluştur
        self.splash_window = tk.Toplevel(self.root)  # Splash penceresi
        self.splash_window.title(f"{self.app_info['name']} - Loading...")  # Başlık
        
        # Ekran ölçüleri
        screen_width = self.splash_window.winfo_screenwidth()  # Ekran genişliği
        screen_height = self.splash_window.winfo_screenheight()  # Ekran yüksekliği
        
        # Splash ekranı boyutu
        width = min(1600, int(screen_width * 0.95))  # maksimum: 1600
        height = min(1000, int(screen_height * 0.95))  # maksimum: 1000

        
        # Merkezi pozisyon
        x = (screen_width - width) // 2  # X konumu
        y = (screen_height - height) // 2  # Y konumu
        
        # Pencere boyutunu ve konumunu ayarla
        self.splash_window.geometry(f"{width}x{height}+{x}+{y}")  # Geometri
        
        # Pencere dekorasyonlarını kaldır
        self.splash_window.overrideredirect(True)  # Çerçevesiz
        
        # Yarı saydam ve modern görünüm
        self.splash_window.attributes("-alpha", 0.98)  # Saydamlık
        self.splash_window.attributes("-topmost", True)  # Üstte
        
        # Ana canvas 
        self.canvas = tk.Canvas(self.splash_window, highlightthickness=0, bg="#0A0A0A")  # Kanvas
        self.canvas.pack(fill="both", expand=True)  # Yerleşim
        
        # Guard AI teması - premium gradient
        gradient_colors = [
            "#0D1421",  # Derin lacivert
            "#1A237E",  # Guard primary
            "#3420ED",  # Guard accent
            "#6366F1",  # Modern indigo
            "#8B5CF6",  # Premium purple
        ]
        
        # Gelişmiş gradient arka plan
        self._create_premium_gradient(width, height, gradient_colors)  # Gradient oluştur
        
        # Geometrik pattern overlay
        self._create_geometric_pattern(width, height)  # Pattern
        
        # Parçacık sistemi
        self._initialize_particles(width, height)  # Parçacıklar
        
        # Dekoratif ışık efektleri
        self._create_light_effects(width, height)  # Işıklar
        
        # Logo bölümü
        self._create_logo_section(width, height)  # Logo
        
        # Marka ve başlık
        self._create_branding_section(width, height)  # Başlık
        
        # İlerleme göstergesi
        self._create_progress_section(width, height)  # İlerleme
        
        # Alt bilgi
        self._create_footer_section(width, height)  # Alt bilgi
        
        # Animasyonları başlat
        self._start_animations()  # Animasyonlar

    def _create_premium_gradient(self, width, height, colors):
        """Premium gradient arka plan oluştur."""
        for i in range(height):
            # Normalize pozisyon
            pos = i / height
            
            # Dalgalı efekt
            wave_offset = math.sin(i / 80) * 0.02  # Dalga
            wave_pos = max(0, min(1, pos + wave_offset))  # Pozisyon
            
            # Renk segmentlerini hesapla
            segment_size = 1.0 / (len(colors) - 1)  # Segment boyutu
            segment_index = min(len(colors) - 2, int(wave_pos / segment_size))  # Segment indeksi
            local_t = (wave_pos - segment_index * segment_size) / segment_size  # Yerel t
            
            # İki rengi karıştır
            color1 = colors[segment_index]  # İlk renk
            color2 = colors[segment_index + 1]  # İkinci renk
            
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)  # RGB1
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)  # RGB2
            
            r = int(r1 * (1 - local_t) + r2 * local_t)  # Kırmızı
            g = int(g1 * (1 - local_t) + g2 * local_t)  # Yeşil
            b = int(b1 * (1 - local_t) + b2 * local_t)  # Mavi
            
            # Dinamik parlaklık
            brightness = 1.0 + 0.1 * math.sin(i / 60 + time.time())  # Parlaklık
            r = min(255, int(r * brightness))  # Kırmızı sınır
            g = min(255, int(g * brightness))  # Yeşil sınır
            b = min(255, int(b * brightness))  # Mavi sınır
            
            color = f'#{r:02x}{g:02x}{b:02x}'  # Hex renk
            self.canvas.create_line(0, i, width, i, fill=color)  # Çizgi çiz

    def _create_geometric_pattern(self, width, height):
        """Geometrik pattern overlay."""
        # Hexagon pattern
        for x in range(0, width, 100):
            for y in range(0, height, 100):
                if random.random() < 0.3:  # %30 ihtimal
                    size = random.randint(20, 40)  # Boyut
                    self._draw_hexagon(x, y, size, "#FFFFFF", alpha=0.02)  # Hexagon çiz
        
        # Circuit lines
        for _ in range(15):
            x1 = random.randint(0, width)  # Başlangıç x
            y1 = random.randint(0, height)  # Başlangıç y
            x2 = x1 + random.randint(-200, 200)  # Bitiş x
            y2 = y1 + random.randint(-200, 200)  # Bitiş y
            
            self.canvas.create_line(x1, y1, x2, y2, 
                                   fill="#6366F1", width=1, stipple="gray25")  # Çizgi çiz

    def _draw_hexagon(self, x, y, size, color, alpha=1.0):
        """Hexagon çiz."""
        points = []
        for i in range(6):
            angle = i * math.pi / 3  # Açı
            px = x + size * math.cos(angle)  # X koordinatı
            py = y + size * math.sin(angle)  # Y koordinatı
            points.extend([px, py])  # Noktaları ekle
        
        self.canvas.create_polygon(points, outline=color, fill="", width=1, stipple="gray12")  # Poligon çiz

    def _initialize_particles(self, width, height):
        """Gelişmiş parçacık sistemi."""
        self.particles = []
        for _ in range(80):
            particle = {
                'x': random.randint(0, width),  # X pozisyonu
                'y': random.randint(0, height),  # Y pozisyonu
                'size': random.uniform(0.5, 2.5),  # Boyut
                'speed': random.uniform(0.1, 0.8),  # Hız
                'direction': random.uniform(0, 2 * math.pi),  # Yön
                'alpha': random.uniform(0.2, 0.8),  # Saydamlık
                'color': random.choice(['#FFFFFF', '#6366F1', '#8B5CF6', '#3420ED']),  # Renk
                'pulse': random.uniform(0, 2 * math.pi),  # Nabız
                'id': None  # Canvas ID
            }
            self.particles.append(particle)  # Parçacığı ekle

    def _create_light_effects(self, width, height):
        """Dekoratif ışık efektleri."""
        # Ana ışık kaynağı
        light_size = width // 4  # Boyut
        self.canvas.create_oval(
            width//2 - light_size//2, -light_size//2,
            width//2 + light_size//2, light_size//2,
            fill="#3420ED", outline="", stipple="gray12")  # Işık çiz
        
        # Yan ışık efektleri
        for i, (x_ratio, y_ratio, color) in enumerate([
            (0.1, 0.2, "#6366F1"),
            (0.9, 0.3, "#8B5CF6"),
            (0.15, 0.8, "#3420ED"),
            (0.85, 0.7, "#6366F1")
        ]):
            x = int(width * x_ratio)  # X pozisyonu
            y = int(height * y_ratio)  # Y pozisyonu
            size = random.randint(80, 120)  # Boyut
            
            self.canvas.create_oval(
                x - size//2, y - size//2,
                x + size//2, y + size//2,
                fill=color, outline="", stipple="gray25")  # Işık çiz

    def _create_logo_section(self, width, height):
        """Logo bölümü - İkon daha yukarıda."""
        try:
            # Logo dosyası yolu
            logo_paths = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons", "logo.png"),
                os.path.join("resources", "icons", "logo.png"),
                "logo.png"
            ]
            
            logo_loaded = False
            for logo_path in logo_paths:
                if os.path.exists(logo_path):
                    try:
                        # Logo'yu yükle ve işle
                        orig_img = Image.open(logo_path)  # Görüntüyü aç
                        
                        # Görüntü iyileştirmeleri
                        enhancer = ImageEnhance.Sharpness(orig_img)  # Keskinlik
                        img = enhancer.enhance(2.2)  # Keskinlik artır
                        enhancer = ImageEnhance.Brightness(img)  # Parlaklık
                        img = enhancer.enhance(1.4)  # Parlaklık artır
                        enhancer = ImageEnhance.Contrast(img)  # Kontrast
                        img = enhancer.enhance(1.3)  # Kontrast artır
                        
                        # Logo boyutu
                        logo_size = min(700, int(min(width, height) * 0.40))

                        img = img.resize((logo_size, logo_size), Image.LANCZOS)  # Yeniden boyutlandır
                        
                        # Glow efekti
                        glow_img = img.filter(ImageFilter.GaussianBlur(radius=20))  # Bulanıklık
                        glow_img = ImageEnhance.Brightness(glow_img).enhance(2.5)  # Parlaklık artır
                        
                        # PhotoImage'leri oluştur
                        self.glow_img = ImageTk.PhotoImage(glow_img)  # Glow görüntüsü
                        self.logo_img = ImageTk.PhotoImage(img)  # Logo görüntüsü
                        
                        # Glow label
                        self.glow_label = tk.Label(
                            self.splash_window,
                            image=self.glow_img,
                            bg='#1A237E',
                            bd=0
                        )
                        self.glow_label.place(relx=0.5, rely=0.15, anchor="center")  
                        # Ana logo
                        self.logo_label = tk.Label(
                            self.splash_window,
                            image=self.logo_img,
                            bg='#1A237E',
                            bd=0
                        )
                        self.logo_label.place(relx=0.5, rely=0.15, anchor="center")  
                        
                        logo_loaded = True
                        break
                        
                    except Exception as e:
                        logging.debug(f"Logo yükleme hatası ({logo_path}): {e}")
                        continue
            
            if not logo_loaded:
                # Logo yoksa alternatif
                self._create_alternative_logo(width, height)  # Alternatif logo
                
        except Exception as e:
            logging.warning(f"Logo bölümü oluşturulurken hata: {e}")
            self._create_alternative_logo(width, height)  # Alternatif logo

    def _create_alternative_logo(self, width, height):
        """Alternatif logo oluştur - Daha yukarıda."""
        # Canvas üzerinde alternatif logo
        logo_x = width // 2  # X merkezi
        logo_y = int(height * 0.2)  # Y yukarı taşı (0.3 -> 0.2)
        logo_size = 100  # Boyut
        
        # Dış çember
        self.canvas.create_oval(
            logo_x - logo_size, logo_y - logo_size,
            logo_x + logo_size, logo_y + logo_size,
            outline="#3420ED", width=4, fill="#1A237E")  # Çember
        
        # İç çember
        self.canvas.create_oval(
            logo_x - logo_size//2, logo_y - logo_size//2,
            logo_x + logo_size//2, logo_y + logo_size//2,
            outline="#6366F1", width=3, fill="#3420ED")  # İç çember
        
        # G harfi
        self.canvas.create_text(
            logo_x, logo_y,
            text="G",
            font=("Segoe UI", 48, "bold"),
            fill="#FFFFFF")  # G harfi

    def _create_branding_section(self, width, height):
        """Marka ve başlık bölümü - Daha yukarıda."""
        brand_frame = tk.Frame(self.splash_window, bg="#1A237E", bd=0)  # Çerçeve
        brand_frame.place(relx=0.5, rely=0.55, anchor="center")  # Yukarı taşı (0.5 -> 0.35)
        
        # Ana başlık
        title_label = tk.Label(
            brand_frame,
            text=self.app_info['name'],
            font=("Segoe UI", 64, "bold"),
            fg="#FFFFFF",
            bg="#1A237E",
            bd=0
        )
        title_label.pack()  # Yerleşim
        
        # Alt başlık
        self.subtitle_var = tk.StringVar(value=self.app_info['description'])  # Değişken
        subtitle_label = tk.Label(
            brand_frame,
            textvariable=self.subtitle_var,
            font=("Segoe UI", 18, "italic"),
            fg="#A5B4FC",
            bg="#1A237E",
            bd=0
        )
        subtitle_label.pack(pady=(10, 0))  # Yerleşim
        
        # Teknoloji etiketi
        tech_text = " • ".join(self.app_info['tech_stack'])  # Teknolojiler
        tech_label = tk.Label(
            brand_frame,
            text=f"• {tech_text} •",
            font=("Segoe UI", 12),
            fg="#6366F1",
            bg="#1A237E",
            bd=0
        )
        tech_label.pack(pady=(15, 0))  # Yerleşim

    def _create_progress_section(self, width, height):
        """İlerleme göstergesi bölümü."""
        progress_frame = tk.Frame(self.splash_window, bg="#1A237E", bd=0)  # Çerçeve
        progress_frame.place(relx=0.5, rely=0.72, anchor="center")  # Yerleşim
        
        # İlerleme çubuğu container
        progress_container = tk.Frame(progress_frame, bg="#0D1421", bd=2, relief="flat")  # Kapsayıcı
        progress_container.pack(fill="x", padx=50)  # Yerleşim
        
        # İlerleme çubuğu
        progress_width = int(width * 0.7)  # Genişlik
        progress_height = 18  # Yükseklik
        
        self.progress_canvas = tk.Canvas(
            progress_container,
            width=progress_width,
            height=progress_height,
            bg="#0D1421",
            highlightthickness=0,
            bd=0
        )
        self.progress_canvas.pack(padx=6, pady=8)  

        
        # İlerleme durumu
        self.progress_value = 0  # Başlangıç
        
        # Durum metni
        self.status_var = tk.StringVar(value="Guard AI sistemi başlatılıyor...")  # Değişken
        status_label = tk.Label(
            progress_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 13, "bold"),
            fg="#FFFFFF",
            bg="#1A237E",
            bd=0
        )
        status_label.pack(pady=(15, 5))  # Yerleşim
        
        # Detay metni
        self.detail_var = tk.StringVar(value="Lütfen bekleyin...")  # Değişken
        detail_label = tk.Label(
            progress_frame,
            textvariable=self.detail_var,
            font=("Segoe UI", 10),
            fg="#A5B4FC",
            bg="#1A237E",
            bd=0
        )
        detail_label.pack()  # Yerleşim

    def _create_footer_section(self, width, height):
        """Alt bilgi bölümü."""
        footer_frame = tk.Frame(self.splash_window, bg="#1A237E", bd=0)  # Çerçeve
        footer_frame.place(relx=0.5, rely=0.92, anchor="center")  # Yerleşim
        
        # Versiyon bilgisi
        version_text = f"{self.app_info['name']} v{self.app_info['version']} | YOLOv11 Enhanced | © {self.app_info['year']} {self.app_info['author']}"  # Metin
        version_label = tk.Label(
            footer_frame,
            text=version_text,
            font=("Segoe UI", 10),
            fg="#6B7280",
            bg="#1A237E",
            bd=0
        )
        version_label.pack()  # Yerleşim
        
        # Sistem bilgisi
        import platform
        system_info = f"Python {platform.python_version()} | {platform.system()} {platform.release()}"  # Sistem
        system_label = tk.Label(
            footer_frame,
            text=system_info,
            font=("Consolas", 8),
            fg="#4B5563",
            bg="#1A237E",
            bd=0
        )
        system_label.pack()  # Yerleşim

    def _start_animations(self):
        """Tüm animasyonları başlat."""
        # Parçacık animasyonu
        self._animate_particles()  # Parçacıklar
        
        # Logo pulse animasyonu
        if hasattr(self, 'logo_label'):
            self._animate_logo_pulse()  # Logo nabız
        
        # İlerleme çubuğu animasyonu
        self._animate_progress_bar()  # İlerleme

    def _animate_particles(self):
        """Gelişmiş parçacık animasyonu."""
        if not self.splash_window or not self.splash_window.winfo_exists():
            return
            
        try:
            width = self.splash_window.winfo_width()  # Genişlik
            height = self.splash_window.winfo_height()  # Yükseklik
            
            for particle in self.particles:
                # Eski parçacığı sil
                if particle['id']:
                    self.canvas.delete(particle['id'])  # Sil
                
                # Parçacığı hareket ettir
                particle['x'] += math.cos(particle['direction']) * particle['speed']  # X hareket
                particle['y'] += math.sin(particle['direction']) * particle['speed']  # Y hareket
                
                # Pulse efekti
                particle['pulse'] += 0.1  # Nabız artır
                pulse_size = particle['size'] * (1 + 0.3 * math.sin(particle['pulse']))  # Boyut
                
                # Ekran sınırları kontrolü
                if particle['x'] < 0 or particle['x'] > width:
                    particle['direction'] = math.pi - particle['direction']  # X yön değiştir
                if particle['y'] < 0 or particle['y'] > height:
                    particle['direction'] = -particle['direction']  # Y yön değiştir
                
                # Pozisyonu sınırla
                particle['x'] = max(0, min(width, particle['x']))  # X sınır
                particle['y'] = max(0, min(height, particle['y']))  # Y sınır
                
                # Parçacığı çiz
                particle['id'] = self.canvas.create_oval(
                    particle['x'] - pulse_size, particle['y'] - pulse_size,
                    particle['x'] + pulse_size, particle['y'] + pulse_size,
                    fill=particle['color'], outline="", stipple="gray25")  # Oval çiz
            
            # Animasyonu devam ettir
            self.splash_window.after(50, self._animate_particles)  # Zamanlayıcı
            
        except tk.TclError:
            # Pencere kapanmış
            pass
        except Exception as e:
            logging.debug(f"Parçacık animasyon hatası: {e}")

    def _animate_logo_pulse(self):
        """Logo pulse animasyonu."""
        if not self.splash_window or not self.splash_window.winfo_exists():
            return
            
        try:
            if not hasattr(self, 'pulse_scale'):
                self.pulse_scale = 1.0  # Başlangıç ölçeği
                self.pulse_direction = 1  # Yön
            
            # Pulse hesaplama
            self.pulse_scale += 0.003 * self.pulse_direction  # Ölçek artır/azalt
            
            if self.pulse_scale >= 1.08:
                self.pulse_direction = -1  # Yön değiştir
            elif self.pulse_scale <= 0.98:
                self.pulse_direction = 1  # Yön değiştir
            
            # Animasyonu devam ettir
            self.splash_window.after(30, self._animate_logo_pulse)  # Zamanlayıcı
            
        except tk.TclError:
            # Pencere kapanmış
            pass
        except Exception as e:
            logging.debug(f"Logo pulse hatası: {e}")

    def _animate_progress_bar(self):
        """İlerleme çubuğu animasyonu."""
        if not self.splash_window or not self.splash_window.winfo_exists():
            return
            
        try:
            # Mevcut çubukları temizle
            self.progress_canvas.delete("progress")  # Temizle
            
            # İlerleme çubuğu boyutları
            canvas_width = self.progress_canvas.winfo_width()  # Genişlik
            canvas_height = self.progress_canvas.winfo_height()  # Yükseklik
            
            if canvas_width <= 1:  # Canvas henüz oluşturulmamış
                self.splash_window.after(100, self._animate_progress_bar)  # Bekle
                return
            
            # İlerleme çubuğunu çiz
            if self.progress_value > 0:
                bar_width = int(canvas_width * (self.progress_value / 100))  # Çubuk genişliği
                
                # Gradient ilerleme çubuğu
                for i in range(bar_width):
                    pos = i / canvas_width  # Pozisyon
                    
                    # Renk gradyasyonu
                    if pos < 0.5:
                        t = pos * 2
                        r = int(52 * (1-t) + 99 * t)   # #3420ED -> #6366F1
                        g = int(32 * (1-t) + 102 * t)
                        b = int(237 * (1-t) + 241 * t)
                    else:
                        t = (pos - 0.5) * 2
                        r = int(99 * (1-t) + 139 * t)   # #6366F1 -> #8B5CF6
                        g = int(102 * (1-t) + 92 * t)
                        b = int(241 * (1-t) + 246 * t)
                    
                    self.progress_canvas.create_line(
                        i, 0, i, canvas_height,
                        fill=f"#{r:02x}{g:02x}{b:02x}",
                        tags="progress")  # Çizgi çiz
                
                # Parlama efekti
                if bar_width > 10:
                    glow_x = bar_width - 5  # Parlama pozisyonu
                    for i in range(10):
                        alpha = 1 - (i / 10)  # Saydamlık
                        brightness = int(255 * alpha)  # Parlaklık
                        
                        self.progress_canvas.create_line(
                            glow_x + i, 0, glow_x + i, canvas_height,
                            fill=f"#{brightness:02x}{brightness:02x}{255:02x}",
                            tags="progress")  # Parlama çiz
            
            # Animasyonu devam ettir
            self.splash_window.after(50, self._animate_progress_bar)  # Zamanlayıcı
            
        except tk.TclError:
            # Pencere kapanmış
            pass
        except Exception as e:
            logging.debug(f"Progress bar hatası: {e}")

    def _start_initialization_simulation(self):
        """Gerçekçi başlatma simülasyonu başlat."""
        self.current_step = 0  # Başlangıç adımı
        self._simulate_next_step()  # İlk adımı simüle et

    def _simulate_next_step(self):
        """Sonraki başlatma adımını simüle et."""
        if (not self.splash_window or 
            not self.splash_window.winfo_exists() or 
            self.current_step >= len(self.initialization_steps)):
            return
        
        try:
            step = self.initialization_steps[self.current_step]  # Adımı al
            
            # Durum metnini güncelle
            self.status_var.set(step["text"])  # Durum
            
            # Detay metni
            details = [
                "Modüller kontrol ediliyor...",
                "Bağımlılıklar yükleniyor...",
                "Yapılandırma dosyaları okunuyor...",
                "Ağ bağlantıları test ediliyor...",
                "Sistem kaynaklarını optimize ediyor..."
            ]
            self.detail_var.set(random.choice(details))  # Rastgele detay
            
            # İlerleme değerini güncelle
            target_progress = step["progress"]  # Hedef ilerleme
            self._animate_progress_to_target(target_progress)  # Animasyon
            
            # Sonraki adıma geç
            self.current_step += 1  # Adım artır
            next_delay = int(step["duration"] * 1000)  # Gecikme
            self.splash_window.after(next_delay, self._simulate_next_step)  # Zamanlayıcı
            
        except Exception as e:
            logging.debug(f"Initialization step hatası: {e}")

    def _animate_progress_to_target(self, target):
        """İlerleme değerini hedefe doğru yumuşak animasyon."""
        if abs(self.progress_value - target) < 1:
            self.progress_value = target  # Hedefe ulaşıldı
            return
        
        # Yumuşak geçiş
        diff = target - self.progress_value  # Fark
        self.progress_value += diff * 0.1  # Adım adım artır
        
        if abs(diff) > 0.5:
            self.splash_window.after(50, lambda: self._animate_progress_to_target(target))  # Devam et

    def _close_splash(self):
        """Yumuşak geçiş ile splash ekranını kapat."""
        if not self.splash_window or not self.splash_window.winfo_exists():
            self.root.deiconify()  # Ana pencereyi göster
            return
            
        try:
            # Son durum
            self.status_var.set("Guard AI hazır!")  # Durum
            self.detail_var.set("Ana ekrana yönlendiriliyor...")  # Detay
            self.progress_value = 100  # İlerleme
            
            # Kısa bir bekleme
            self.splash_window.update()  # Güncelle
            time.sleep(0.5)  # Bekle
            
            # Yumuşak kapanış animasyonu
            for alpha in range(10, -1, -1):
                self.splash_window.attributes('-alpha', alpha / 10)  # Saydamlık azalt
                self.splash_window.update()  # Güncelle
                time.sleep(0.04)  # Bekle
            
            # Splash'ı kapat
            self.splash_window.destroy()  # Pencereyi yok et
            self.splash_window = None  # Sıfırla
            
            # Ana pencereyi göster
            self.root.deiconify()  # Göster
            self.root.update()  # Güncelle
            self.root.focus_force()  # Fokus
            self.root.attributes('-topmost', True)  # Üstte
            self.root.after(100, lambda: self.root.attributes('-topmost', False))  # Üstte sıfırla
            
        except Exception as e:
            logging.error(f"Splash kapatma hatası: {e}")
            # Hata durumunda temiz kapatma
            try:
                if self.splash_window:
                    self.splash_window.destroy()  # Pencereyi yok et
                self.root.deiconify()  # Ana pencereyi göster
            except:
                pass