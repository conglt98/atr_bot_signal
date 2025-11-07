# Signal Logging Documentation
## Hướng Dẫn Sử Dụng Tính Năng Logging

---

## 📝 Tổng Quan

Khi chạy script production (`atr_breakout_production.py`), mỗi khi có signal (LONG hoặc SHORT), tất cả thông tin sẽ được **tự động log vào file** để dễ dàng trace và phân tích sau này.

---

## 📁 File Log

**Vị trí:** `logs/signals.log` (mặc định)

**Format:** JSON (dễ parse và đọc)

**Tự động tạo:** Thư mục `logs/` sẽ được tạo tự động nếu chưa có

---

## ⚙️ Cấu Hình

Trong file `config.py`:

```python
# Signal logging configuration
SIGNAL_LOG_FILE: str = "logs/signals.log"  # Đường dẫn file log
ENABLE_SIGNAL_LOGGING: bool = True         # Bật/tắt logging
```

**Tùy chỉnh:**
- Đổi đường dẫn file: `SIGNAL_LOG_FILE = "my_signals.log"`
- Tắt logging: `ENABLE_SIGNAL_LOGGING = False`

---

## 📊 Thông Tin Được Log

Mỗi signal được log với đầy đủ thông tin:

### 1. **Timestamp & Time**
- `timestamp`: Thời gian phát hiện signal (ISO format)
- `candle_time`: Thời gian của nến tạo signal

### 2. **Signal Information**
- `signal.type`: "LONG" hoặc "SHORT"
- `signal.value`: 1 (LONG) hoặc -1 (SHORT)

### 3. **Price Information**
- `price.current`: Giá hiện tại
- `price.entry`: Giá vào lệnh (= current price)
- `price.stop_loss`: Giá stop loss
- `price.take_profit`: Giá take profit

### 4. **Technical Indicators**
- `indicators.ema20`: Giá trị EMA20
- `indicators.ema50`: Giá trị EMA50
- `indicators.atr`: Giá trị ATR
- `indicators.rsi`: Giá trị RSI
- `indicators.adx`: Giá trị ADX

### 5. **Breakout Levels**
- `breakout_levels.long`: Mức breakout cho LONG
- `breakout_levels.short`: Mức breakout cho SHORT

### 6. **Filter Status**
- `filters.volume_ok`: Volume filter pass/fail
- `filters.adx_ok`: ADX filter pass/fail
- `filters.volume`: Volume hiện tại
- `filters.volume_avg`: Volume trung bình
- `filters.volume_ratio`: Tỷ lệ volume

### 7. **Trend**
- `trend`: "UPTREND", "DOWNTREND", hoặc "SIDEWAYS"

### 8. **Risk:Reward**
- `risk_reward.ratio`: R:R ratio (3.5)
- `risk_reward.stop_loss_distance`: Khoảng cách stop loss (USD)
- `risk_reward.take_profit_distance`: Khoảng cách take profit (USD)
- `risk_reward.stop_loss_pct`: Stop loss (%)
- `risk_reward.take_profit_pct`: Take profit (%)

### 9. **Strategy Parameters**
- Tất cả tham số strategy tại thời điểm signal
- `atr_breakout_multiplier`, `atr_tp_rr`, `rsi_long_min`, etc.

### 10. **Signal Reason**
- `signal_reason`: Lý do tạo signal (text description)

---

## 📄 Ví Dụ Log Entry

```json
{
  "timestamp": "2025-11-07T11:08:12.123456",
  "candle_time": "2025-11-07T04:08:00",
  "signal": {
    "type": "LONG",
    "value": 1
  },
  "price": {
    "current": 101683.20,
    "entry": 101683.20,
    "stop_loss": 101605.89,
    "take_profit": 101953.81
  },
  "indicators": {
    "ema20": 101842.58,
    "ema50": 101927.50,
    "atr": 77.31,
    "rsi": 60.5,
    "adx": 53.42
  },
  "breakout_levels": {
    "long": 101935.35,
    "short": 101749.81
  },
  "filters": {
    "volume_ok": true,
    "adx_ok": true,
    "volume": 2800,
    "volume_avg": 1000,
    "volume_ratio": 2.8
  },
  "trend": "UPTREND",
  "risk_reward": {
    "ratio": 3.5,
    "stop_loss_distance": 77.31,
    "take_profit_distance": 270.61,
    "stop_loss_pct": 0.076,
    "take_profit_pct": 0.266
  },
  "strategy_params": {
    "atr_breakout_multiplier": 1.2,
    "atr_sl_multiplier": 1.0,
    "atr_tp_rr": 3.5,
    "rsi_long_min": 55,
    "rsi_long_max": 65,
    "rsi_short_min": 35,
    "rsi_short_max": 45,
    "volume_multiplier": 2.5,
    "adx_threshold": 25
  },
  "signal_reason": "Price broke above EMA20 + 1.2×ATR with RSI 60.5"
}

================================================================================
```

---

## 🔍 Cách Sử Dụng Log File

### 1. **Xem Logs**
```bash
# Xem toàn bộ logs
cat logs/signals.log

# Xem logs gần nhất
tail -50 logs/signals.log

# Xem logs theo thời gian
grep "2025-11-07" logs/signals.log
```

### 2. **Parse JSON với Python**
```python
import json

# Đọc và parse logs
with open('logs/signals.log', 'r') as f:
    content = f.read()
    
# Split by separator
entries = content.split('='*80)

for entry in entries:
    if entry.strip():
        try:
            data = json.loads(entry.strip())
            print(f"Signal: {data['signal']['type']} at {data['timestamp']}")
            print(f"Entry: ${data['price']['entry']:.2f}")
            print(f"Stop Loss: ${data['price']['stop_loss']:.2f}")
            print(f"Take Profit: ${data['price']['take_profit']:.2f}")
            print("-" * 40)
        except:
            pass
```

### 3. **Phân Tích Signals**
- Đếm số signals: `grep -c '"type": "LONG"' logs/signals.log`
- Tìm signals trong khoảng thời gian
- So sánh indicators giữa các signals
- Phân tích win/loss rate của signals đã log

---

## 💡 Lợi Ích

1. ✅ **Trace Signals:** Dễ dàng xem lại tất cả signals đã phát hiện
2. ✅ **Phân Tích:** So sánh signals thắng/thua
3. ✅ **Debug:** Kiểm tra tại sao signal được tạo
4. ✅ **Backtest:** So sánh với kết quả thực tế
5. ✅ **Tối Ưu:** Phân tích để cải thiện strategy

---

## ⚠️ Lưu Ý

- File log sẽ **tăng dần** theo thời gian
- Nên **rotate logs** định kỳ (xóa hoặc archive logs cũ)
- File log có thể **lớn** nếu chạy lâu
- Có thể **tắt logging** trong config nếu không cần

---

*Tính năng logging giúp bạn theo dõi và phân tích tất cả signals một cách chuyên nghiệp*

