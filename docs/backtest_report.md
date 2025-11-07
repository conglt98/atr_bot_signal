# Báo Cáo Backtest BTCUSDT Scalping Bot
## Dữ liệu thực từ Binance Futures (30 ngày)

**Ngày tạo báo cáo:** 2025-11-07  
**Thời gian backtest:** 2025-10-07 20:05:00 đến 2025-11-07 03:04:00  
**Tổng số nến:** 43,620 nến (1 phút)  
**Nguồn dữ liệu:** Binance Futures - BTC/USDT:USDT (Perpetual)

---

## Thông Số Backtest

| Tham số | Giá trị |
|---------|---------|
| Vốn ban đầu (giả định) | $100 USD |
| Rủi ro mỗi lệnh | $5 USD |
| Phí giao dịch mỗi lệnh | $1.4 USD (round-trip) |
| Stop Loss | 0.15% giá vào lệnh |
| Timeframe | 1 phút |

---

## Kết Quả Backtest Chi Tiết

### 1. EMA(9/21) Crossover Strategy

| Chỉ số | Giá trị |
|--------|---------|
| **Tổng số lệnh** | 1,228 |
| **Lệnh thắng** | 331 |
| **Lệnh thua** | 897 |
| **Tỷ lệ thắng** | **26.95%** |
| **Tổng P/L** | **-$1,535.53** |
| **Reward:Risk Ratio** | 2:1 |
| **Take Profit** | 0.30% |

**Phân tích:**
- Chiến lược tạo ra nhiều tín hiệu (1,228 lệnh trong 30 ngày)
- Tỷ lệ thắng thấp (26.95%) - chỉ 1/4 lệnh thắng
- Mặc dù R:R = 2:1, nhưng tỷ lệ thắng quá thấp khiến tổng P/L âm
- Phí giao dịch ($1.4 × 1,228 = $1,719.2) là yếu tố chính gây lỗ

---

### 2. Bollinger Bands + RSI Strategy

| Chỉ số | Giá trị |
|--------|---------|
| **Tổng số lệnh** | 1,106 |
| **Lệnh thắng** | 502 |
| **Lệnh thua** | 604 |
| **Tỷ lệ thắng** | **45.39%** |
| **Tổng P/L** | **-$1,584.56** |
| **Reward:Risk Ratio** | 1.5:1 |
| **Take Profit** | 0.225% |

**Phân tích:**
- Tỷ lệ thắng tốt nhất trong 3 chiến lược (45.39%)
- Số lệnh thắng (502) gần bằng số lệnh thua (604)
- Tuy nhiên, R:R = 1.5:1 không đủ bù đắp phí giao dịch
- Phí giao dịch ($1.4 × 1,106 = $1,548.4) vẫn là vấn đề lớn

---

### 3. MACD Crossover Strategy

| Chỉ số | Giá trị |
|--------|---------|
| **Tổng số lệnh** | 2,025 |
| **Lệnh thắng** | 582 |
| **Lệnh thua** | 1,443 |
| **Tỷ lệ thắng** | **28.74%** |
| **Tổng P/L** | **-$2,643.41** |
| **Reward:Risk Ratio** | 2:1 |
| **Take Profit** | 0.30% |

**Phân tích:**
- Tạo ra nhiều tín hiệu nhất (2,025 lệnh) - quá nhiều
- Tỷ lệ thắng thấp (28.74%)
- Phí giao dịch rất cao ($1.4 × 2,025 = $2,835)
- Chiến lược kém hiệu quả nhất trong 3 chiến lược

---

## So Sánh Tổng Quan

| Chiến lược | Số lệnh | Win Rate | Tổng P/L | Xếp hạng |
|------------|---------|----------|----------|----------|
| **EMA(9/21) Crossover** | 1,228 | 26.95% | **-$1,535.53** | 🥇 Tốt nhất (ít lỗ nhất) |
| **Bollinger+RSI** | 1,106 | **45.39%** | -$1,584.56 | 🥈 Win rate cao nhất |
| **MACD Crossover** | 2,025 | 28.74% | -$2,643.41 | 🥉 Kém nhất |

---

## Phân Tích Nguyên Nhân Thua Lỗ

### 1. **Phí Giao Dịch Quá Cao**
- Mỗi lệnh mất $1.4 phí (round-trip)
- Với số lượng lệnh lớn (1,000-2,000 lệnh), tổng phí rất cao:
  - EMA: $1,719.2
  - Bollinger+RSI: $1,548.4
  - MACD: $2,835.0

### 2. **Tỷ Lệ Thắng Thấp**
- Chỉ có Bollinger+RSI đạt 45.39% win rate
- EMA và MACD chỉ đạt ~27-29% win rate
- Với R:R = 1.5-2:1, cần win rate ≥ 40-50% để có lợi nhuận

### 3. **Nhiều Tín Hiệu Giả (False Signals)**
- Scalping trên khung 1 phút tạo ra nhiều tín hiệu nhiễu
- Market noise trên timeframe ngắn khiến các chỉ báo kém chính xác

### 4. **Stop Loss Quá Chặt**
- Stop loss 0.15% có thể bị "stop out" bởi biến động ngắn hạn
- Trong thị trường biến động, giá có thể chạm stop trước khi đạt take profit

---

## Khuyến Nghị

### ⚠️ **Cảnh Báo**
**Tất cả 3 chiến lược đều thua lỗ trong giai đoạn backtest này.** Không nên sử dụng với tiền thật mà không có:
- Tối ưu hóa tham số kỹ lưỡng
- Forward testing trên tài khoản demo
- Quản lý rủi ro chặt chẽ

### 🔧 **Cải Thiện Cần Thiết**

1. **Giảm Phí Giao Dịch**
   - Tìm sàn có phí thấp hơn (maker fee < 0.02%)
   - Sử dụng lệnh limit thay vì market để giảm phí
   - Tăng khoảng cách stop/take profit để giảm số lệnh

2. **Lọc Tín Hiệu Tốt Hơn**
   - Thêm bộ lọc volume (chỉ trade khi volume cao)
   - Kết hợp nhiều chỉ báo để xác nhận tín hiệu
   - Tránh trade trong thời gian biến động thấp

3. **Tối Ưu Tham Số**
   - Test các giá trị R:R khác nhau (1.5, 2.0, 2.5)
   - Điều chỉnh stop loss (0.1%, 0.15%, 0.2%)
   - Thử các timeframe khác (5m, 15m) để giảm noise

4. **Quản Lý Rủi Ro**
   - Giảm số lệnh mỗi ngày (tối đa 10-20 lệnh)
   - Thêm điều kiện dừng khi lỗ liên tiếp
   - Chỉ trade trong giờ có thanh khoản cao

5. **Cải Thiện Chiến Lược Bollinger+RSI**
   - Đây là chiến lược có win rate tốt nhất (45.39%)
   - Cần tối ưu để tăng R:R hoặc giảm số lệnh
   - Có tiềm năng nhất để phát triển thêm

---

## Kết Luận

Backtest trên dữ liệu thực 30 ngày cho thấy:
- **Không có chiến lược nào có lợi nhuận** trong giai đoạn này
- **Bollinger+RSI** có win rate tốt nhất (45.39%) nhưng vẫn lỗ do phí
- **EMA Crossover** ít lỗ nhất (-$1,535.53) nhưng win rate thấp
- **MACD Crossover** kém hiệu quả nhất với số lệnh quá nhiều

**Scalping trên khung 1 phút là rất khó khăn** do:
- Phí giao dịch cao
- Nhiều tín hiệu giả
- Biến động ngắn hạn khó dự đoán

**Khuyến nghị:** Nên test trên timeframe lớn hơn (5m, 15m) hoặc tối ưu hóa kỹ lưỡng trước khi sử dụng với tiền thật.

---

## Dữ Liệu Backtest

- **File dữ liệu:** `btcusdt_ohlcv.csv`
- **Số nến:** 43,620
- **Thời gian:** 2025-10-07 20:05:00 đến 2025-11-07 03:04:00
- **Exchange:** Binance Futures
- **Symbol:** BTC/USDT:USDT (Perpetual)

---

*Báo cáo được tạo tự động từ kết quả backtest thực tế*

