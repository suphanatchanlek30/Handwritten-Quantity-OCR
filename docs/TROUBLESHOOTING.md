# Troubleshooting

เริ่มจาก `python scripts/check_environment.py` เสมอ; คำสั่งนี้บอก Python, package, backend และ model cache ที่ระบบพบ

## ติดตั้งไม่ผ่าน

- `No matching distribution found for paddlepaddle`: ใช้ Python 3.11 และสร้าง `.venv` ใหม่ด้วย `bash scripts/setup_mac.sh`
- `import cv2` ผิดปกติ: ถอน `opencv-python` และ `opencv-python-headless` ที่ซ้ำ แล้วรัน setup script อีกครั้ง
- Apple Silicon ต้องรัน native `arm64`; อย่าเปิด shell ผ่าน Rosetta

## ดาวน์โหลดหรือโหลดโมเดลไม่ได้

- รัน `python scripts/check_environment.py --download` ขณะมี network
- หาก network มีปัญหา IPv6 ให้ใช้ `network.force_ipv4: true` ซึ่งเป็นค่า default
- เครื่อง offline ต้อง copy model cache จากเครื่องที่เตรียมไว้แล้วตามที่ script รายงาน

## หา table หรือ crop ไม่ถูก

1. รัน `python -m qty_ocr.cli run --input INPUT.jpg --output outputs/debug --debug`
2. เปิด `detected_table.png`, `aligned_grid.png` และ `qty_overlay.png`
3. ตรวจว่าภาพเห็นขอบตารางครบและหัวคอลัมน์ qty อ่านได้
4. ปรับ `layout.*` หรือใช้ template config สำหรับฟอร์มคงที่

## ค่าที่อ่านต้องตรวจซ้ำ

เปิด `results.csv`, `summary.md` และ crop ของแถวนั้น. ความหมายของ `review_reasons` อยู่ใน [Decision logic](DECISION_LOGIC.md). อย่าลด confidence threshold โดยไม่มีชุด label ที่ยืนยันแล้ว

## GPU

GPU ใช้ได้เฉพาะ NVIDIA/CUDA ที่ runtime รองรับ. หากระบุ `--device gpu` แล้วระบบหยุด ให้แก้ runtime ก่อน; ระบบตั้งใจไม่ fallback เป็น CPU แบบเงียบ ๆ
