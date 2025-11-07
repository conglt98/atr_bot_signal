# ATR Breakout Strategy - Production Script

## 🚀 Hướng Dẫn Sử Dụng

### Cài Đặt Dependencies

```bash
pip install pandas numpy ccxt colorama
```

### Chạy Script

```bash
python atr_breakout_production.py
```

### Tính Năng

✅ **Real-time Data**: Tự động fetch dữ liệu mới nhất từ Binance mỗi 60 giây  
✅ **Màu Sắc Rõ Ràng**: 
   - 🟢 Xanh lá: LONG signal, UPTREND, giá trị tốt
   - 🔴 Đỏ: SHORT signal, DOWNTREND, cảnh báo
   - 🟡 Vàng: Thông tin quan trọng
   - 🔵 Xanh dương: Header, separator

✅ **Highlight Signals**: 
   - LONG signal: Nền xanh lá, chữ trắng, in đậm
   - SHORT signal: Nền đỏ, chữ trắng, in đậm

✅ **Thông Tin Đầy Đủ**:
   - Market data (giá, trend, thời gian)
   - Technical indicators (EMA, ATR, RSI, ADX, Volume)
   - Trading signal với entry, stop loss, take profit
   - Strategy parameters

### Output Format

Script sẽ hiển thị:

1. **Header**: Thông tin strategy và exchange
2. **Market Data**: Giá hiện tại, trend, thời gian
3. **Technical Indicators**: 
   - EMA20, EMA50 và relationship
   - ATR và breakout levels
   - RSI với ranges
   - ADX với status (PASS/FAIL)
   - Volume với ratio và status
4. **Trading Signal**: 
   - Highlight rõ ràng khi có signal
   - Entry price, Stop Loss, Take Profit
   - Risk:Reward ratio
5. **Strategy Parameters**: Tất cả tham số đã tối ưu

### Dừng Script

Nhấn `Ctrl+C` để dừng script.

### Lưu Ý

- Script tự động refresh mỗi 60 giây
- Cần kết nối internet để fetch data
- Cần API key nếu exchange yêu cầu (hiện tại không cần cho public data)

---

## 📊 Tham Số Tối Ưu

| Tham Số | Giá Trị |
|---------|---------|
| ATR Breakout Multiplier (k) | 1.2 |
| R:R Ratio | 2.5:1 |
| RSI Long Range | 55-65 |
| RSI Short Range | 35-45 |
| Volume Multiplier | 2.5× |
| ADX Threshold | 25 |
| Stop Loss | 1.0× ATR |
| Take Profit | 2.5× ATR |

---

## 🎯 Ví Dụ Output

Khi có LONG signal:
```
🎯 TRADING SIGNAL
--------------------------------------------------------------------------------
                    LONG SIGNAL                    
                    BUY NOW                    
Entry Price: $67,234.56
Stop Loss: $66,789.12 (-0.66%)
Take Profit: $67,912.34 (+1.01%)
Risk:Reward = 1:2.5
```

Khi không có signal:
```
🎯 TRADING SIGNAL
--------------------------------------------------------------------------------
No Signal
Status: Waiting for breakout above $67,450.00
```

---

*Script được tối ưu từ backtest với lợi nhuận +$54.70 trên 30 ngày*

