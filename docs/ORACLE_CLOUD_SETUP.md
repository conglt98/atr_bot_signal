# Hướng dẫn Setup ATR Breakout Bot trên Oracle Cloud

## 📋 Mục lục
1. [Đăng ký Oracle Cloud](#1-đăng-ký-oracle-cloud)
2. [Tạo Compute Instance](#2-tạo-compute-instance)
3. [Kết nối SSH](#3-kết-nối-ssh)
4. [Cài đặt Docker](#4-cài-đặt-docker)
5. [Deploy Bot](#5-deploy-bot)
6. [Chạy Bot](#6-chạy-bot)
7. [Quản lý Bot](#7-quản-lý-bot)

---

## 1. Đăng ký Oracle Cloud

### Bước 1: Truy cập Oracle Cloud
- Vào: https://www.oracle.com/cloud/free/
- Click **"Start for Free"**

### Bước 2: Đăng ký tài khoản
- Điền thông tin:
  - Email
  - Tên, Họ
  - Số điện thoại
  - Quốc gia
- **Yêu cầu thẻ tín dụng** (không bị charge nếu chỉ dùng free tier)

### Bước 3: Xác thực
- Xác thực email và số điện thoại
- Nhập thông tin thẻ tín dụng (chỉ để verify, không bị charge)

### Bước 4: Đăng nhập
- Sau khi đăng ký xong, đăng nhập vào: https://cloud.oracle.com/

---

## 2. Tạo Compute Instance

### Bước 1: Vào Compute
1. Đăng nhập Oracle Cloud Console
2. Menu **☰** → **Compute** → **Instances**

### Bước 2: Tạo Instance
1. Click **"Create Instance"**

2. **Name**: `atr-bot` (hoặc tên bạn muốn)

3. **Image and Shape**:
   - **Image**: Chọn **"Canonical Ubuntu 22.04"** (hoặc 20.04)
   - **Shape**: Click **"Edit"** → Chọn **"VM.Standard.A1.Flex"** (Always Free)
   - **OCPUs**: `2` (tối đa free)
   - **Memory**: `12 GB` (tối đa free)

4. **Networking**:
   - **Virtual Cloud Network**: Tạo mới hoặc dùng mặc định
   - **Subnet**: Tạo mới hoặc dùng mặc định
   - **Public IP**: ✅ **Assign a public IPv4 address** (QUAN TRỌNG!)

5. **Add SSH keys**:
   - **Option 1**: Paste public key nếu bạn đã có
   - **Option 2**: Click **"Save Private Key"** và **"Save Public Key"** để tải về
   - ⚠️ **LƯU LẠI PRIVATE KEY** - bạn sẽ cần nó để SSH!

6. Click **"Create"**

### Bước 3: Đợi Instance Ready
- Đợi 2-5 phút để instance khởi động
- Status sẽ chuyển từ **"Provisioning"** → **"Running"**

### Bước 4: Lấy Public IP
- Sau khi instance running, copy **Public IP address**

---

## 3. Kết nối SSH

### Trên Mac/Linux:

```bash
# Nếu bạn đã có private key
chmod 400 /path/to/your/private-key
ssh -i /path/to/your/private-key ubuntu@<PUBLIC_IP>

# Hoặc nếu bạn tải key từ Oracle Cloud
chmod 400 ~/Downloads/ssh-key-<timestamp>.key
ssh -i ~/Downloads/ssh-key-<timestamp>.key ubuntu@<PUBLIC_IP>
```

### Trên Windows:
- Dùng **PuTTY** hoặc **WSL** hoặc **Git Bash**

### Lần đầu kết nối:
- Sẽ hỏi "Are you sure you want to continue connecting?" → Gõ `yes`

---

## 4. Cài đặt Docker

### Bước 1: Update system
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### Bước 2: Cài đặt Docker
```bash
# Cài đặt dependencies
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group (để không cần sudo)
sudo usermod -aG docker $USER

# Logout và login lại để áp dụng thay đổi
exit
```

### Bước 3: Kết nối lại SSH và verify Docker
```bash
# SSH lại
ssh -i /path/to/your/private-key ubuntu@<PUBLIC_IP>

# Verify Docker
docker --version
docker ps
```

---

## 5. Deploy Bot

### Option 1: Upload code từ máy local (Khuyến nghị)

#### Bước 1: Tạo tarball trên máy local
```bash
# Trên máy Mac của bạn
cd /Users/conglt/Documents/project_code

# Tạo file tar với các file cần thiết
tar -czf atr-bot.tar.gz \
    atr_breakout_production.py \
    utils.py \
    backtest_optimized.py \
    config.py \
    requirements.txt \
    Dockerfile \
    docker-compose.yml \
    .dockerignore
```

#### Bước 2: Upload lên server
```bash
# Từ máy local, upload file
scp -i /path/to/your/private-key atr-bot.tar.gz ubuntu@<PUBLIC_IP>:~/
```

#### Bước 3: Extract trên server
```bash
# SSH vào server
ssh -i /path/to/your/private-key ubuntu@<PUBLIC_IP>

# Extract file
cd ~
tar -xzf atr-bot.tar.gz
mkdir -p atr-bot
mv *.py *.txt Dockerfile docker-compose.yml .dockerignore atr-bot/
cd atr-bot
```

### Option 2: Clone từ Git (nếu bạn có repo)

```bash
# Trên server
cd ~
git clone <your-repo-url> atr-bot
cd atr-bot
```

### Option 3: Tạo file trực tiếp trên server

```bash
# Tạo thư mục
mkdir -p ~/atr-bot
cd ~/atr-bot

# Tạo các file bằng nano hoặc vim
nano atr_breakout_production.py
# Paste nội dung file và save (Ctrl+X, Y, Enter)

# Làm tương tự cho các file khác:
# - utils.py
# - backtest_optimized.py
# - config.py
# - requirements.txt
# - Dockerfile
# - docker-compose.yml
```

---

## 6. Chạy Bot

### Bước 1: Build Docker image
```bash
cd ~/atr-bot
docker build -t atr-bot:latest .
```

### Bước 2: Chạy với docker-compose (Khuyến nghị)
```bash
# Chạy ở background
docker-compose up -d

# Xem logs
docker-compose logs -f
```

### Hoặc chạy trực tiếp với Docker:
```bash
# Chạy ở background
docker run -d \
    --name atr-bot \
    --restart unless-stopped \
    -v $(pwd)/logs:/app/logs \
    atr-bot:latest

# Xem logs
docker logs -f atr-bot
```

### Bước 3: Verify bot đang chạy
```bash
# Kiểm tra container
docker ps

# Xem logs real-time
docker logs -f atr-bot
```

---

## 7. Quản lý Bot

### Xem logs
```bash
# Với docker-compose
docker-compose logs -f

# Với docker run
docker logs -f atr-bot

# Xem logs file (nếu có)
tail -f ~/atr-bot/logs/signals.log
```

### Dừng bot
```bash
# Với docker-compose
docker-compose down

# Với docker run
docker stop atr-bot
```

### Khởi động lại bot
```bash
# Với docker-compose
docker-compose restart

# Với docker run
docker start atr-bot
```

### Xóa và chạy lại
```bash
# Với docker-compose
docker-compose down
docker-compose up -d --build

# Với docker run
docker stop atr-bot
docker rm atr-bot
docker run -d --name atr-bot --restart unless-stopped -v $(pwd)/logs:/app/logs atr-bot:latest
```

### Update code mới
```bash
# 1. Upload code mới (như bước 5)
# 2. Rebuild image
docker-compose build

# 3. Restart
docker-compose up -d
```

### Cấu hình Firewall (nếu cần)
```bash
# Oracle Cloud có Security List mặc định
# Nếu cần mở port, vào:
# Networking → Virtual Cloud Networks → Security Lists
# Thêm Ingress Rule cho port cần thiết
```

---

## 🔧 Troubleshooting

### Bot không chạy
```bash
# Kiểm tra logs
docker logs atr-bot

# Kiểm tra config
docker exec -it atr-bot cat /app/config.py
```

### Lỗi kết nối API
- Kiểm tra internet: `ping google.com`
- Kiểm tra firewall Oracle Cloud
- Kiểm tra Telegram bot token và chat ID trong config.py

### Bot bị dừng
```bash
# Kiểm tra container status
docker ps -a

# Xem logs lỗi
docker logs atr-bot

# Restart
docker restart atr-bot
```

### Kiểm tra resource usage
```bash
# CPU và Memory
docker stats atr-bot

# Disk space
df -h
```

---

## 📝 Lưu ý quan trọng

1. **Always Free Tier giới hạn**:
   - 2 OCPUs, 12GB RAM
   - 200GB storage
   - Đủ cho bot này

2. **Bảo mật**:
   - Không commit config.py có token vào Git
   - Dùng environment variables nếu cần
   - Giữ private key an toàn

3. **Monitoring**:
   - Check logs thường xuyên
   - Setup Telegram notifications để biết bot status

4. **Backup**:
   - Backup config.py
   - Backup logs nếu cần

---

## 🎉 Hoàn thành!

Bot của bạn giờ đã chạy 24/7 trên Oracle Cloud! 

Kiểm tra Telegram để xem signals hoặc xem logs:
```bash
docker logs -f atr-bot
```

