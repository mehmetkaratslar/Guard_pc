#!/bin/bash
# scripts/docker-setup.sh - Docker kurulum ve başlatma script'i

set -e  # Hata durumunda çık

echo "🛡️  Guard PC App - Docker Setup"
echo "=================================="

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Gerekli dosyaları kontrol et
check_required_files() {
    echo -e "${BLUE}📁 Gerekli dosyalar kontrol ediliyor...${NC}"
    
    required_files=(
        "Dockerfile"
        "docker-compose.yml"
        "requirements.txt"
        ".env"
        "resources/models/fall_model.pt"
        "resources/serviceAccountKey.json"
    )
    
    missing_files=()
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -ne 0 ]]; then
        echo -e "${RED}❌ Eksik dosyalar:${NC}"
        for file in "${missing_files[@]}"; do
            echo -e "${RED}   - $file${NC}"
        done
        echo -e "${YELLOW}💡 .env.example dosyasını .env olarak kopyalayın ve doldurun${NC}"
        echo -e "${YELLOW}💡 YOLOv11 modelinizi resources/models/fall_model.pt olarak yerleştirin${NC}"
        echo -e "${YELLOW}💡 Firebase serviceAccountKey.json dosyasını resources/ dizinine koyun${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Tüm gerekli dosyalar mevcut${NC}"
}

# Docker yüklü mü kontrol et
check_docker() {
    echo -e "${BLUE}🐳 Docker kontrol ediliyor...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker yüklü değil!${NC}"
        echo -e "${YELLOW}💡 Docker'ı yüklemek için: https://docs.docker.com/get-docker/${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose yüklü değil!${NC}"
        echo -e "${YELLOW}💡 Docker Compose'u yüklemek için: https://docs.docker.com/compose/install/${NC}"
        exit 1
    fi
    
    # Docker daemon çalışıyor mu?
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker daemon çalışmıyor!${NC}"
        echo -e "${YELLOW}💡 Docker'ı başlatın: sudo systemctl start docker${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Docker hazır${NC}"
}

# Kamera erişimi kontrolü (Linux)
check_camera() {
    echo -e "${BLUE}📹 Kamera erişimi kontrol ediliyor...${NC}"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [[ ! -e /dev/video0 ]]; then
            echo -e "${YELLOW}⚠️  /dev/video0 bulunamadı. Webcam bağlı mı?${NC}"
        else
            echo -e "${GREEN}✅ Kamera cihazı bulundu: /dev/video0${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Windows/Mac için kamera erişimi Docker Desktop ayarlarından yapılandırılmalı${NC}"
    fi
}

# X11 forwarding ayarla (Linux GUI için)
setup_x11() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "${BLUE}🖥️  X11 forwarding ayarlanıyor...${NC}"
        
        # X11 erişim izni ver
        xhost +local:docker &> /dev/null || true
        
        # DISPLAY değişkenini ayarla
        export DISPLAY=${DISPLAY:-:0}
        echo "DISPLAY=$DISPLAY" >> .env
        
        echo -e "${GREEN}✅ X11 forwarding ayarlandı${NC}"
    fi
}

# Docker build ve run
build_and_run() {
    echo -e "${BLUE}🔨 Docker image build ediliyor...${NC}"
    
    # Önceki container'ları durdur
    docker-compose down &> /dev/null || true
    
    # Image build et
    docker-compose build --no-cache
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Build başarılı${NC}"
    else
        echo -e "${RED}❌ Build başarısız${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}🚀 Uygulama başlatılıyor...${NC}"
    
    # Container'ları başlat
    docker-compose up -d
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Uygulama başlatıldı${NC}"
        show_access_info
    else
        echo -e "${RED}❌ Başlatma başarısız${NC}"
        docker-compose logs
        exit 1
    fi
}

# Erişim bilgilerini göster
show_access_info() {
    # IP adresini al
    if command -v hostname &> /dev/null; then
        IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    else
        IP="localhost"
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Guard PC App Docker'da çalışıyor!${NC}"
    echo "=================================================="
    echo -e "${BLUE}📱 Mobil Erişim:${NC} http://$IP:5000/mobile"
    echo -e "${BLUE}🌐 API Status:${NC}   http://$IP:5000/api/status"
    echo -e "${BLUE}🖥️  X11 Client:${NC}  http://$IP:8080 (GUI için)"
    echo "=================================================="
    echo ""
    echo -e "${YELLOW}📋 Faydalı komutlar:${NC}"
    echo "  docker-compose logs -f          # Logları takip et"
    echo "  docker-compose restart          # Yeniden başlat"
    echo "  docker-compose down             # Durdur"
    echo "  docker-compose exec guard-app bash  # Container'a gir"
    echo ""
}

# Cleanup fonksiyonu
cleanup() {
    echo -e "${BLUE}🧹 Temizlik yapılıyor...${NC}"
    docker-compose down
    docker system prune -f
    echo -e "${GREEN}✅ Temizlik tamamlandı${NC}"
}

# Ana fonksiyon
main() {
    case "${1:-setup}" in
        "setup"|"start")
            check_required_files
            check_docker
            check_camera
            setup_x11
            build_and_run
            ;;
        "stop")
            echo -e "${BLUE}⏹️  Uygulama durduruluyor...${NC}"
            docker-compose down
            echo -e "${GREEN}✅ Durduruldu${NC}"
            ;;
        "restart")
            echo -e "${BLUE}🔄 Yeniden başlatılıyor...${NC}"
            docker-compose restart
            show_access_info
            ;;
        "logs")
            echo -e "${BLUE}📋 Loglar gösteriliyor...${NC}"
            docker-compose logs -f
            ;;
        "cleanup")
            cleanup
            ;;
        "status")
            echo -e "${BLUE}📊 Container durumu:${NC}"
            docker-compose ps
            ;;
        *)
            echo "Kullanım: $0 {setup|start|stop|restart|logs|cleanup|status}"
            echo ""
            echo "  setup    - İlk kurulum ve başlatma (varsayılan)"
            echo "  start    - Başlat"
            echo "  stop     - Durdur"
            echo "  restart  - Yeniden başlat"
            echo "  logs     - Logları göster"
            echo "  cleanup  - Temizlik yap"
            echo "  status   - Durum göster"
            exit 1
            ;;
    esac
}

# Script'i çalıştır
main "$@"