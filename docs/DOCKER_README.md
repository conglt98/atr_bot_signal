# Docker Setup cho ATR Breakout Bot

## 🐳 Quick Start

### Build Docker Image
```bash
docker build -t atr-bot:latest .
```

### Chạy với Docker Compose (Khuyến nghị)
```bash
# Chạy ở background
docker-compose up -d

# Xem logs
docker-compose logs -f

# Dừng
docker-compose down
```

### Chạy trực tiếp với Docker
```bash
# Chạy ở background
docker run -d \
    --name atr-bot \
    --restart unless-stopped \
    -v $(pwd)/logs:/app/logs \
    atr-bot:latest

# Xem logs
docker logs -f atr-bot

# Dừng
docker stop atr-bot
docker rm atr-bot
```

## 📁 Files Structure

```
.
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose config
├── .dockerignore          # Files to exclude from build
├── requirements.txt       # Python dependencies
├── atr_breakout_production.py  # Main script
├── utils.py               # Utilities
├── backtest_optimized.py  # Indicators
├── config.py             # Configuration
└── logs/                  # Logs directory (created automatically)
```

## ⚙️ Configuration

Chỉnh sửa `config.py` trước khi build để cấu hình:
- Exchange settings
- Strategy parameters
- Telegram notifications
- Update interval

## 📝 Logs

Logs được lưu trong thư mục `logs/`:
- `logs/signals.log` - Trading signals (nếu ENABLE_SIGNAL_LOGGING = True)

## 🔄 Update Code

1. Sửa code
2. Rebuild image: `docker-compose build`
3. Restart: `docker-compose up -d`

## 📚 Xem thêm

- Chi tiết setup Oracle Cloud: [ORACLE_CLOUD_SETUP.md](./ORACLE_CLOUD_SETUP.md)

