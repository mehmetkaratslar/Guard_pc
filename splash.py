import tkinter as tk
import time
import threading
import os
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import math
import random

class SplashScreen:
    """Ultra modern ve etkileyici uygulama açılış ekranı, giriş sayfasına yumuşak geçiş."""
    
    def __init__(self, root, duration=3.0):
        """
        Args:
            root (tk.Tk): Ana pencere
            duration (float, optional): Açılış ekranı süresi (saniye)
        """
        self.root = root
        self.duration = duration
        self.splash_window = None
        self.particles = []  # Parçacık animasyonu için
        
        # Ana pencereyi gizle
        self.root.withdraw()
        
        # Splash ekranını göster
        self._show_splash()
        
        # Belirli bir süre sonra ana pencereyi göster
        threading.Thread(target=self._show_main_after_delay, daemon=True).start()
    
    def _show_splash(self):
        """Ultra modern ve etkileyici splash ekranını gösterir."""
        # Yeni bir pencere oluştur
        self.splash_window = tk.Toplevel(self.root)
        self.splash_window.title("Guard")
        
        # Ekran ölçüleri
        screen_width = self.splash_window.winfo_screenwidth()
        screen_height = self.splash_window.winfo_screenheight()
        
        # Splash ekranı boyutu (ekranın %70'i)
        width = int(screen_width * 0.7)
        height = int(screen_height * 0.7)
        
        # Merkezi pozisyon
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # Pencere boyutunu ve konumunu ayarla
        self.splash_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Pencere dekorasyonlarını kaldır ve borderless yap
        self.splash_window.overrideredirect(True)
        
        # Pencereyi yarı saydam ve yuvarlak köşeli yapmak için
        self.splash_window.attributes("-alpha", 0.97)
        
        # Ana canvas 
        self.canvas = tk.Canvas(self.splash_window, highlightthickness=0, bg="#121212")
        self.canvas.pack(fill="both", expand=True)
        
        # Daha modern ve premium görünümlü gradient
        gradient_colors = [
            "#1A237E",  # Derin indigo (başlangıç)
            "#303F9F",  # Koyu indigo (orta)
            "#3949AB",  # İndigo (orta)
            "#3F51B5",  # Orta indigo (bitiş)
        ]
        
        # Animasyonlu arkaplan için değişkenler
        self.wave_offset = 0
        
        # Ana gradient arka plan
        for i in range(height):
            # Yüzde olarak geçerli pozisyon
            percent = i / height
            
            # Dalgalı gradient için pozisyonu modifiye et
            wave_percent = percent + math.sin(i / 50) * 0.03
            wave_percent = max(0, min(1, wave_percent))
            
            # Renk hesaplama
            if wave_percent < 0.33:
                t = wave_percent * 3  # 0 -> 1
                r1, g1, b1 = int(gradient_colors[0][1:3], 16), int(gradient_colors[0][3:5], 16), int(gradient_colors[0][5:7], 16)
                r2, g2, b2 = int(gradient_colors[1][1:3], 16), int(gradient_colors[1][3:5], 16), int(gradient_colors[1][5:7], 16)
            elif wave_percent < 0.66:
                t = (wave_percent - 0.33) * 3  # 0 -> 1
                r1, g1, b1 = int(gradient_colors[1][1:3], 16), int(gradient_colors[1][3:5], 16), int(gradient_colors[1][5:7], 16)
                r2, g2, b2 = int(gradient_colors[2][1:3], 16), int(gradient_colors[2][3:5], 16), int(gradient_colors[2][5:7], 16)
            else:
                t = (wave_percent - 0.66) * 3  # 0 -> 1
                r1, g1, b1 = int(gradient_colors[2][1:3], 16), int(gradient_colors[2][3:5], 16), int(gradient_colors[2][5:7], 16)
                r2, g2, b2 = int(gradient_colors[3][1:3], 16), int(gradient_colors[3][3:5], 16), int(gradient_colors[3][5:7], 16)
            
            # İki rengi karıştır
            r = int(r1 * (1 - t) + r2 * t)
            g = int(g1 * (1 - t) + g2 * t)
            b = int(b1 * (1 - t) + b2 * t)
            
            # Ekstra ışıltı efekti
            sparkle_effect = random.randint(0, 100) < 2  # %2 ihtimal
            if sparkle_effect:
                r = min(255, r + 30)
                g = min(255, g + 30)
                b = min(255, b + 30)
            
            color = f'#{r:02x}{g:02x}{b:02x}'
            self.canvas.create_line(0, i, width, i, fill=color, smooth=True)
        
        # Efekt parçacıkları (yıldız benzeri)
        for _ in range(50):
            particle = {
                'x': random.randint(0, width),
                'y': random.randint(0, height),
                'size': random.uniform(1, 3),
                'speed': random.uniform(0.2, 1.5),
                'alpha': random.uniform(0.3, 1.0),
                'id': None
            }
            self.particles.append(particle)
        
        # Parçacık animasyonu
        self._animate_particles()
        
        # Dekoratif ışık efektleri
        # Üst sağ ışık dairesi
        light_radius = width // 6
        self.canvas.create_oval(width - light_radius * 1.5, -light_radius // 2, 
                                width + light_radius // 2, light_radius, 
                                fill="#7986CB", outline="", stipple="gray25")
        
        # Alt sol ışık dairesi
        self.canvas.create_oval(-light_radius // 2, height - light_radius * 1.2, 
                                light_radius, height + light_radius // 2, 
                                fill="#9FA8DA", outline="", stipple="gray25")
                                
        # Arka plan animasyonu
        self._animate_background()
                                
        # Logo ve marka bölümü
        try:
            logo_path = os.path.join(
                os.path.dirname(__file__), 
                "resources", 
                "icons", 
                "logo.png"
            )
            
            if os.path.exists(logo_path):
                # Logo'yu işle
                orig_img = Image.open(logo_path)
                
                # Daha iyi görünüm için görüntü işleme
                enhancer = ImageEnhance.Sharpness(orig_img)
                img = enhancer.enhance(2.0)  # Keskinliği artır
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.3)  # Parlaklığı artır
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)  # Kontrastı artır
                
                # Logo boyutu - daha büyük
                logo_size = int(min(width, height) * 0.45)
                img = img.resize((logo_size, logo_size), Image.LANCZOS)
                
                # Etkileyici glow efekti
                glow_img = img.filter(ImageFilter.GaussianBlur(radius=15))
                glow_img = ImageEnhance.Brightness(glow_img).enhance(1.8)
                
                # Glow ve logo görüntüleri
                self.glow_img = ImageTk.PhotoImage(glow_img)
                self.logo_img = ImageTk.PhotoImage(img)
                
                # Glow efekti arka planda
                self.glow_label = tk.Label(
                    self.splash_window,
                    image=self.glow_img,
                    bg='#303F9F'  # Gradient ile uyumlu renk
                )
                self.glow_label.place(relx=0.5, rely=0.4, anchor="center")
                
                # Ana logo
                self.logo_label = tk.Label(
                    self.splash_window,
                    image=self.logo_img,
                    bg='#303F9F'  # Gradient ile uyumlu renk
                )
                self.logo_label.place(relx=0.5, rely=0.4, anchor="center")
                
                # Gelişmiş pulsing animasyonu
                self._start_pulse_animation()
                
        except Exception as e:
            print(f"Logo yüklenirken hata: {e}")
        
        # Markalama bölümü (daha etkileyici)
        brand_frame = tk.Frame(self.splash_window, bg="#303F9F")
        brand_frame.place(relx=0.5, rely=0.72, anchor="center")
        
        # GUARD yazısı - ultra modern ve bold
        app_name = tk.Label(
            brand_frame,
            text="GUARD",
            font=("Segoe UI", 58, "bold"),
            fg="#FFFFFF",
            bg="#303F9F"
        )
        app_name.pack()
        
        # Animasyonlu alt başlık
        self.subtitle_var = tk.StringVar(value="Akıllı Düşme Algılama Sistemi")
        app_desc = tk.Label(
            brand_frame,
            textvariable=self.subtitle_var,
            font=("Segoe UI", 22, "italic"),
            fg="#E8EAF6",  # Açık indigo
            bg="#303F9F"
        )
        app_desc.pack(pady=(10, 0))
        
        # Alt başlık animasyonu
        self._animate_subtitle()
        
        # Modern ilerleme göstergesi
        progress_frame = tk.Frame(self.splash_window, bg="#303F9F", padx=width//5)
        progress_frame.place(relx=0.5, rely=0.85, anchor="center")
        
        # İlerleme çubuğu
        progress_width = width * 0.6
        progress_height = 8  # İnce ve şık
        
        # İlerleme çubuğu konteyneri
        progress_container = tk.Frame(progress_frame, bg="#1A237E", padx=2, pady=2, bd=0)
        progress_container.pack(fill="x")
        
        # İlerleme çubuğu
        self.progress_canvas = tk.Canvas(
            progress_container,
            width=progress_width,
            height=progress_height,
            bg="#1A237E",
            highlightthickness=0,
            bd=0
        )
        self.progress_canvas.pack(fill="x")
        
        # İlerleme durumu
        self.progress_value = 0
        
        # İlerleme metni
        self.loading_var = tk.StringVar(value="Başlatılıyor...")
        loading_label = tk.Label(
            progress_frame,
            textvariable=self.loading_var,
            font=("Segoe UI", 11),
            fg="#E8EAF6",
            bg="#303F9F"
        )
        loading_label.pack(pady=(10, 0))
        
        # İlerleme çubuğu animasyonu
        self._animate_progress_bar()
        
        # Yükleniyor metni animasyonu
        self._animate_loading_text()
        
        # Versiyon ve telif bilgisi
        version = tk.Label(
            self.splash_window,
            text="Versiyon 1.0.0 | © 2025 Guard Technologies",
            font=("Segoe UI", 10),
            fg="#E8EAF6",
            bg="#303F9F"
        )
        version.place(relx=0.5, rely=0.95, anchor="center")
        
        # Ekstra görsellik: Gelişmiş ışıma efekti
        light_beam = self.canvas.create_polygon(
            width/2, height/2,
            width/2-200, height,
            width/2+200, height,
            fill="#7986CB", stipple="gray12"
        )

    def _animate_particles(self):
        """Parçacık animasyonu."""
        if not self.splash_window:
            return
            
        try:
            # Her parçacığı güncelle
            for particle in self.particles:
                # Eski parçacığı sil
                if particle['id']:
                    self.canvas.delete(particle['id'])
                
                # Parçacığı yukarı hareket ettir
                particle['y'] -= particle['speed']
                
                # Ekrandan çıkarsa yeniden konumlandır
                if particle['y'] < 0:
                    particle['y'] = self.splash_window.winfo_height() + 5
                    particle['x'] = random.randint(0, self.splash_window.winfo_width())
                    particle['alpha'] = random.uniform(0.3, 1.0)
                    particle['size'] = random.uniform(1, 3)
                
                # Parçacığı çiz
                size = particle['size']
                alpha = int(particle['alpha'] * 255)
                color = f"#{255:02x}{255:02x}{255:02x}{alpha:02x}"  # RGBA formatı
                particle['id'] = self.canvas.create_oval(
                    particle['x']-size, particle['y']-size,
                    particle['x']+size, particle['y']+size,
                    fill="white", outline=""
                )
            
            # Animasyonu devam ettir
            self.splash_window.after(50, self._animate_particles)
        except:
            # Pencere kapanmış olabilir
            pass
        
    def _animate_background(self):
        """Dalgalı arka plan animasyonu."""
        if not self.splash_window:
            return
            
        try:
            # Animasyonu devam ettir
            self.splash_window.after(100, self._animate_background)
        except:
            # Pencere kapanmış olabilir
            pass
        
    def _start_pulse_animation(self):
        """Logo için nabız animasyonu."""
        if not self.splash_window:
            return
            
        try:
            # Nabız değişkenleri
            if not hasattr(self, 'pulse_scale'):
                self.pulse_scale = 1.0
                self.pulse_direction = -1
                self.pulse_min = 0.95
                self.pulse_max = 1.05
                self.pulse_step = 0.005
            
            # Ölçeği güncelle
            self.pulse_scale += self.pulse_step * self.pulse_direction
            
            # Yön değiştirme
            if self.pulse_scale <= self.pulse_min:
                self.pulse_direction = 1
            elif self.pulse_scale >= self.pulse_max:
                self.pulse_direction = -1
            
            # Glow etiketini güncelle
            if hasattr(self, 'glow_label') and self.glow_label.winfo_exists():
                # Glow için alfa değerini hesapla
                alpha = 0.7 + 0.3 * ((self.pulse_scale - self.pulse_min) / (self.pulse_max - self.pulse_min))
                
                # Glow rengini güncelle
                r, g, b = 121, 134, 203  # #7986CB
                r = int(r * alpha)
                g = int(g * alpha)
                b = int(b * alpha)
                self.glow_label.configure(bg=f"#{r:02x}{g:02x}{b:02x}")
            
            # Animasyonu devam ettir
            self.splash_window.after(40, self._start_pulse_animation)
        except:
            # Pencere kapanmış olabilir
            pass
    
    def _animate_subtitle(self):
        """Alt başlık metni animasyonu."""
        if not self.splash_window:
            return
            
        try:
            # Metin seçenekleri
            subtitles = [
                "Akıllı Düşme Algılama Sistemi",
                "Güvenliğiniz İçin Geliştirildi",
                "7/24 Kesintisiz Koruma",
                "Hızlı & Anlık Bildirimler"
            ]
            
            # Metin indeksini takip et
            if not hasattr(self, 'subtitle_index'):
                self.subtitle_index = 0
                self.subtitle_delay = 0
            
            # Gecikme sayacını artır
            self.subtitle_delay += 1
            
            # Metin değişimi
            if self.subtitle_delay >= 30:  # ~3 saniye
                self.subtitle_delay = 0
                self.subtitle_index = (self.subtitle_index + 1) % len(subtitles)
                self.subtitle_var.set(subtitles[self.subtitle_index])
            
            # Animasyonu devam ettir
            self.splash_window.after(100, self._animate_subtitle)
        except:
            # Pencere kapanmış olabilir
            pass
    
    def _animate_progress_bar(self):
        """İlerleme çubuğu animasyonu."""
        if not self.splash_window:
            return
            
        try:
            # Mevcut ilerleme çubuğunu temizle
            self.progress_canvas.delete("progress")
            
            # İlerleme değerini artır
            if self.progress_value < 100:
                # Gerçekçi ilerleme simülasyonu
                if self.progress_value < 30:
                    self.progress_value += random.uniform(1.5, 3)
                elif self.progress_value < 60:
                    self.progress_value += random.uniform(0.8, 1.8)
                elif self.progress_value < 85:
                    self.progress_value += random.uniform(0.5, 1.2)
                else:
                    self.progress_value += random.uniform(0.2, 0.5)
                    
                self.progress_value = min(100, self.progress_value)
            
            # İlerleme çubuğu boyutları
            progress_width = self.progress_canvas.winfo_width()
            progress_height = self.progress_canvas.winfo_height()
            
            # İlerleme çubuğunu çiz
            bar_width = int(progress_width * (self.progress_value / 100))
            
            # Ana ilerleme çubuğu - parlak gradient
            for i in range(bar_width):
                # Pozisyon yüzdesi
                pos = i / progress_width
                
                # Renk gradyasyonu
                if pos < 0.5:
                    t = pos * 2
                    r1, g1, b1 = 100, 181, 246  # #64B5F6 (açık mavi)
                    r2, g2, b2 = 30, 136, 229   # #1E88E5 (orta mavi)
                else:
                    t = (pos - 0.5) * 2
                    r1, g1, b1 = 30, 136, 229   # #1E88E5 (orta mavi)
                    r2, g2, b2 = 21, 101, 192   # #1565C0 (koyu mavi)
                
                r = int(r1 * (1 - t) + r2 * t)
                g = int(g1 * (1 - t) + g2 * t)
                b = int(b1 * (1 - t) + b2 * t)
                
                self.progress_canvas.create_line(
                    i, 0, i, progress_height,
                    fill=f"#{r:02x}{g:02x}{b:02x}",
                    tags="progress"
                )
            
            # Parlama efekti
            if bar_width > 0:
                # Parlama genişliği
                glow_width = 20
                for i in range(min(glow_width, bar_width)):
                    # Parlaklık yüzdesi (kenardan uzaklaştıkça azalır)
                    alpha = 1 - (i / glow_width)
                    
                    # Parlak mavi ton
                    r, g, b = 144, 202, 249  # #90CAF9
                    
                    # Parlaklık efekti için renk ayarı
                    r = int(r * alpha + 255 * (1 - alpha))
                    g = int(g * alpha + 255 * (1 - alpha))
                    b = int(b * alpha + 255 * (1 - alpha))
                    
                    self.progress_canvas.create_line(
                        bar_width - i, 0, bar_width - i, progress_height,
                        fill=f"#{r:02x}{g:02x}{b:02x}",
                        width=1,
                        tags="progress"
                    )
            
            # Animasyonu devam ettir
            self.splash_window.after(50, self._animate_progress_bar)
            
            # İlerleme tamamlandığında yükleme mesajını değiştir
            if self.progress_value >= 100:
                self.loading_var.set("Hazır... Giriş ekranına yönlendiriliyor")
        except:
            # Pencere kapanmış olabilir
            pass
    
    def _animate_loading_text(self):
        """Yükleniyor metni animasyonu."""
        if not self.splash_window:
            return
            
        try:
            # Mevcut metni al
            current_text = self.loading_var.get()
            
            # Animasyonu atla
            if "Hazır" in current_text:
                self.splash_window.after(100, self._animate_loading_text)
                return
            
            # Mesaj listesi
            loading_messages = [
                "Başlatılıyor...",
                "Modeller yükleniyor...",
                "Algılama sistemi hazırlanıyor...",
                "Yapay zeka modülü başlatılıyor...",
                "Ağ bağlantıları kuruluyor...",
                "Bildirim sistemi yapılandırılıyor...",
                "Kullanıcı verileri yükleniyor..."
            ]
            
            # Mesaj indeksi takip
            if not hasattr(self, 'message_index'):
                self.message_index = 0
                self.message_delay = 0
            
            # Gecikme sayacını artır
            self.message_delay += 1
            
            # Mesaj değişimi
            if self.message_delay >= 20:  # ~2 saniye
                self.message_delay = 0
                self.message_index = (self.message_index + 1) % len(loading_messages)
                self.loading_var.set(loading_messages[self.message_index])
            
            # Animasyonu devam ettir
            self.splash_window.after(100, self._animate_loading_text)
        except:
            # Pencere kapanmış olabilir
            pass
    
    def _show_main_after_delay(self):
        """Belirli bir süre sonra ana pencereyi gösterir."""
        time.sleep(self.duration)
        
        # İlerleme çubuğunun tamamlanmasını bekle
        time.sleep(1)
        
        # Splash ekranını kapat
        self.root.after(0, self._close_splash)
    
    def _close_splash(self):
        """Yumuşak geçiş ile splash ekranını kapatır."""
        if self.splash_window:
            try:
                # Yumuşak kapanış animasyonu
                for alpha in range(10, -1, -1):
                    self.splash_window.attributes('-alpha', alpha/10)
                    self.splash_window.update()
                    time.sleep(0.03)
                
                self.splash_window.destroy()
                self.splash_window = None
                
                # Root'u göster ve odakla
                self.root.deiconify()
                self.root.update()
                self.root.focus_force()  # Pencereye odaklanmayı zorla
                
            except Exception as e:
                # Hata durumunda temiz bir şekilde kapat
                if self.splash_window:
                    self.splash_window.destroy()
                self.root.deiconify()
                logging.error(f"Splash ekranı kapatılırken hata: {str(e)}")
        else:
            # Splash penceresi yoksa doğrudan root'u göster
            self.root.deiconify()