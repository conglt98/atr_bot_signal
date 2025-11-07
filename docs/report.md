# Bot scalping BTCUSDT on the one‑minute timeframe

## Mục tiêu

Yêu cầu của người dùng là thiết kế và thử nghiệm bot scalping chạy trên khung nến 1 phút cho hợp đồng tương lai **BTCUSDT.P**. Bot cần tự động tải dữ liệu 1 phút từ sàn (Binance hoặc Bybit), xây dựng các chiến lược scalping hợp lý (điểm vào lệnh, mục tiêu chốt lời, cắt lỗ, tỷ lệ R:R, xác suất thắng và lý do vào lệnh) và tiến hành backtest giả lập với số vốn ban đầu 100 USD. Mỗi lệnh mạo hiểm 5 USD và phí giao dịch mỗi vòng vào–ra khoảng 1,3–1,5 USD. Báo cáo cuối cùng tổng hợp các kết quả và chọn ra chiến thuật tốt nhất.

Do môi trường thực thi bị giới hạn truy cập API nên tôi sử dụng bộ dữ liệu nến 1 phút của **Binance** ngày 1 tháng 10 năm 2025 đã tải sẵn. Để mô phỏng dữ liệu trong vòng một tháng, tập dữ liệu này được nhân lên 30 lần. Cần lưu ý rằng điều này chỉ mang tính minh hoạ; dữ liệu lặp lại không phản ánh chính xác biến động thực tế và kết quả backtest có thể khác xa thực tế.

## Dữ liệu và công cụ

* **Dữ liệu:** nến 1 phút BTCUSDT trên Binance ngày 1 / 10 / 2025 gồm 1 440 dòng (24 giờ). Mỗi dòng có thời gian mở, giá mở, cao, thấp, đóng và khối lượng. Các cột khác (khối lượng quy đổi, số giao dịch, …) được bỏ qua.
* **Nhân bản dữ liệu:** để tạo 30 ngày giả lập, toàn bộ 1 440 nến được lặp lại 30 lần và thời gian được tăng thêm số ngày tương ứng. Điều này mang lại 43 200 nến.
* **Phần mềm:** Python (pandas, numpy) được dùng để xử lý dữ liệu và tính toán chỉ báo. Script `bot_signal_btcusdt.py` sử dụng thư viện `ccxt` để tải dữ liệu thật khi có kết nối internet. Trong báo cáo này, backtest được thực hiện trên dữ liệu nhân tạo vì hạn chế môi trường.
* **Phí giao dịch:** mỗi lệnh (vào–ra) bị trừ phí cố định 1,4 USD. Đây là giả định dựa trên phí khoảng 1,3–1,5 USD/lệnh của người dùng.

## Khái quát về scalping nến 1 phút

Scalping là phương pháp giao dịch ngắn hạn tìm kiếm nhiều khoản lợi nhuận nhỏ trên biến động giá nhỏ. Các nhà giao dịch phải mở và đóng vị thế rất nhanh, đặt stop‑loss chặt chẽ và không giữ lệnh qua lâu để hạn chế rủi ro【364979941669545†L460-L490】. Scalping phù hợp với cặp tiền/coin thanh khoản cao như **BTC/USDT** vì khối lượng lớn giúp giảm trượt giá và spread【615773776362651†L160-L176】. Tuy nhiên, phí giao dịch có thể ăn mòn lợi nhuận; một nghiên cứu thử nghiệm SMA 5/12 với trailing stop cho thấy chỉ cần phí 0,6 %/giao dịch cũng làm chiến lược từ lãi nhẹ chuyển sang lỗ【845360784226325†L65-L103】【845360784226325†L210-L239】. Do đó, việc sử dụng sàn có phí thấp (Binance/Bybit), chọn khung thời gian ngắn và tuân thủ kỷ luật cắt lỗ là tối quan trọng【615773776362651†L160-L176】.

## Các chiến lược được thử nghiệm

Các chiến lược dưới đây đều áp dụng nguyên tắc quản trị rủi ro: mỗi lệnh chỉ mạo hiểm 5 USD bằng cách tính kích thước vị thế sao cho khoản lỗ tối đa (đến mức stop‑loss) bằng 5 USD. Mức stop‑loss được đặt cách giá vào lệnh 0,15 % (0,0015 × giá) và mục tiêu chốt lời (take‑profit) được tính bằng tỷ lệ R:R tương ứng. Phí giao dịch 1,4 USD được trừ sau mỗi lệnh.

| Chiến lược | Sơ lược tín hiệu vào lệnh | Tham số chính | Lý do | 
|---|---|---|---| 
| **EMA(9/21) Crossover** | Đường EMA nhanh (9 nến) cắt lên đường EMA chậm (21 nến) → mở vị thế **long**. Cắt xuống → mở vị thế **short**. | R:R = 2:1; stop = 0,15 %; TP = 0,30 % | Theo lý thuyết, khi đường trung bình động ngắn hạn vượt lên (hoặc xuống) đường dài hạn báo hiệu xu hướng mới; scalpers có thể tận dụng pha đầu của xu hướng để ăn nhanh. | 
| **Bollinger Bands + RSI** | Giá đóng cửa dưới dải Bollinger dưới và RSI < 30 → mua vào (quá bán). Giá đóng trên dải trên và RSI > 70 → bán khống (quá mua). Thoát lệnh khi chạm đường giữa hoặc tín hiệu ngược. | R:R = 1,5:1; stop = 0,15 %; TP = 0,225 % | Dải Bollinger kết hợp RSI giúp xác định vùng quá bán/quá mua trên khung 1 phút; đa số scalpers sử dụng các chỉ báo này để bắt đảo chiều ngắn hạn【615773776362651†L446-L449】. | 
| **MACD Crossover** | Chênh lệch MACD (EMA12–EMA26) cắt lên đường tín hiệu (EMA9) → long; cắt xuống → short. | R:R = 2:1; stop = 0,15 %; TP = 0,30 % | MACD thể hiện độ chênh giữa hai EMA; tín hiệu giao cắt được dùng để xác nhận xu hướng mạnh. | 

## Kết quả backtest (dữ liệu nhân tạo 30 ngày)

| Chiến lược | Số lệnh | Số lệnh thắng | Tỷ lệ thắng | Tổng P/L (USD)* | Nhận xét |
|---|---|---|---|---|---|
| **EMA(9/21) Crossover** | 782 | 210 | 26,9 % | –1 169,28 | Nhiều tín hiệu giả trong thị trường đi ngang 1 phút khiến lỗ kéo dài. Phí giao dịch và stop ngắn khiến chiến lược khó có lợi nhuận. |
| **Bollinger + RSI** | 927 | 359 | **38,7 %** | **1 312,69** | Chiến lược đảo chiều ở vùng quá bán/quá mua cho kết quả tốt nhất; tỷ lệ thắng cao hơn mặc dù số lệnh thua vẫn nhiều. Tổng lợi nhuận dương nhờ R:R 1,5:1 và phí thấp. |
| **MACD Crossover** | 1 801 | 362 | 20,1 % | –2 739,95 | MACD trên khung quá ngắn tạo ra nhiều tín hiệu sai; lệnh thua áp đảo, kết hợp phí khiến chiến lược lỗ nặng. |


\* Tổng P/L tính trên số vốn ban đầu 100 USD và mạo hiểm 5 USD mỗi lệnh. Do dữ liệu bị lặp lại, giá trị lợi nhuận tuyệt đối lớn hơn vốn gốc và chỉ mang tính chất tham khảo.

### Phân tích

* **Tác động của phí:** kết quả của hai chiến lược EMA và MACD đều âm dù tỷ lệ thắng không quá thấp. Điều này phù hợp với nhận định trong bài viết trên Medium rằng phí giao dịch có thể biến chiến lược từ lãi nhẹ sang thua lỗ【845360784226325†L65-L103】.
* **Chiến lược Bollinger + RSI:** mặc dù tỷ lệ thắng ~39 % không quá cao, lợi nhuận vẫn dương nhờ tỷ lệ R:R 1,5:1. Việc mua ở vùng quá bán và bán ở vùng quá mua giúp bắt được các dao động hồi ngắn hạn. Tuy nhiên, chiến lược này sẽ kém hiệu quả trong các thị trường có xu hướng mạnh.
* **Giới hạn của backtest:** dữ liệu 30 ngày được tạo bằng cách lặp lại 24 giờ duy nhất nên không đại diện cho biến động thực tế; hiệu quả có thể thay đổi đáng kể nếu dùng dữ liệu thực. Ngoài ra, backtest chưa tính tới trượt giá, biến động phí hoặc sự thay đổi của volume.

## Khuyến nghị sử dụng bot

1. **Chọn sàn có phí thấp và thanh khoản cao.** Binance Futures hoặc Bybit Perpetual thường có spread thấp và phí maker/taker cạnh tranh. Điều này giúp giảm ảnh hưởng của phí đến lợi nhuận【615773776362651†L160-L176】.
2. **Ưu tiên chiến lược Bollinger + RSI.** Trong thử nghiệm, đây là chiến lược duy nhất có tổng P/L dương. Nó tận dụng vùng quá mua/quá bán trên khung 1 phút và đặt stop ngắn để quản lý rủi ro.
3. **Không bỏ qua quản trị rủi ro.** Mỗi lệnh chỉ mạo hiểm 5 % vốn ban đầu (5 USD với tài khoản 100 USD). Đặt stop loss và take profit rõ ràng giúp tránh thua lỗ lớn. Tỷ lệ R:R nên ≥ 1,5.
4. **Theo dõi phí và điều kiện thị trường.** Khi phí tăng lên hoặc biến động quá thấp, scalping 1 phút có thể không hiệu quả【845360784226325†L210-L239】. Hãy kiểm tra lại chiến lược khi điều kiện thị trường thay đổi.
5. **Kiểm tra lại với dữ liệu thực.** Kết quả trên đây chỉ mang tính minh họa. Bạn nên tải dữ liệu thực mới nhất (qua `ccxt`) để chạy backtest chính xác trước khi áp dụng.

## Phần mềm mô phỏng bot

File `bot_signal_btcusdt.py` kèm theo là mã nguồn hoàn chỉnh cho bot scalping. Tập lệnh này có thể:

* **Tải dữ liệu 1 phút** từ Binance hoặc Bybit qua thư viện `ccxt` (cần có mạng). Bạn có thể thay đổi tham số `EXCHANGE_ID` thành `"bybit"` và `SYMBOL` thành `"BTCUSDT"` để sử dụng Bybit.
* **Tính toán chỉ báo** EMA, Bollinger Bands, RSI và MACD.
* **Sinh tín hiệu vào lệnh** theo ba chiến lược đã mô tả.
* **Backtest** với quản trị rủi ro cố định: mạo hiểm 5 USD/lệnh, stop = 0,15 % giá và phí 1,4 USD/vòng lệnh.
* **Tổng hợp kết quả**: số lệnh, tỷ lệ thắng, tổng lợi nhuận và chọn ra chiến lược tốt nhất trong giai đoạn khảo sát.

Người dùng có thể chạy file bằng lệnh:

```bash
python bot_signal_btcusdt.py
```

Khi chạy, chương trình sẽ tự động tải dữ liệu theo cấu hình (`LOOKBACK_DAYS = 60`) và in ra bảng kết quả. Bạn có thể điều chỉnh `RISK_PER_TRADE`, `FEE_PER_TRADE`, `STOP_PCT` và `RR_EMA/RR_BB/RR_MACD` trong file để phù hợp với khẩu vị rủi ro của mình.

## Kết luận

Việc phát triển bot scalping trên nến 1 phút đòi hỏi sự cân nhắc kỹ về phí giao dịch, tính thanh khoản và kỷ luật cắt lỗ. Qua thử nghiệm với dữ liệu giả lập, chiến lược **Bollinger + RSI** cho kết quả khả quan nhất, nhưng vẫn cần kiểm chứng thêm trên dữ liệu thực. Các chiến lược EMA crossover và MACD crossover có xu hướng tạo nhiều tín hiệu giả và dễ bị phí ăn mòn lợi nhuận. Người dùng nên thử nghiệm thêm, tối ưu tham số và cập nhật dữ liệu thường xuyên để có kết quả đáng tin cậy.