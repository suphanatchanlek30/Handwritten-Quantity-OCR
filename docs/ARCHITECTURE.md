# ARCHITECTURE — โครงสร้างระบบและการไหลของข้อมูล

เอกสารนี้อธิบาย **ระบบประกอบด้วยอะไร และข้อมูลไหลผ่านอย่างไร**
- เกณฑ์การตัดสินผลและเหตุผลรีวิวทั้งหมด → [`DECISION_LOGIC.md`](DECISION_LOGIC.md)
- ตัวเลขผลการทดลองที่ใช้เลือกการออกแบบ → [`BENCHMARK.md`](BENCHMARK.md)

---

## 1. ภาพรวม

```text
                       ┌───────────────── pipeline.py: process_document() ─────────────────┐
ภาพ (jpg/png) ─▶ [1] image_loader ─▶ [2] layout (หาตาราง) ─▶ [3] หาคอลัมน์ qty (อ่านหัวตาราง)
                                                                   │
                         ┌─────────────────────────────────────────┘
                         ▼
        [4] roi_extractor: ตัด crop ช่อง qty ทุกแถว
                         │
        ── เฟส 1 (ทุกแถว ไม่ใช้โมเดล) ──────────────────────────────────────
                         ▼
        [5] blank_detector ──ว่าง──▶ blank (null)
                         │ มีลายมือ / ไม่แน่ใจ
                         ▼
        [6] preprocessing: tight_crop (+ digit_segments ถ้าหมึก ≥ 2 กลุ่ม)
                         │
        ── เฟส 2 (ทั้งเอกสาร เรียกโมเดลครั้งเดียว) ─────────────────────────
                         ▼
        [7] recognizer (PP-OCRv5_server_rec, ONNX Runtime) + digit_decoder (บังคับผลเป็น 0–9)
                         ▼
        [8] postprocessing.decide(): ตัดสินค่า + เหตุผลรีวิว
                         ▼
        exporter (results.json / results.csv / summary.md) + visualization (ภาพ debug)
```

- ทุกขั้นเป็นฟังก์ชันแยกในไฟล์ของตัวเอง ทดสอบเดี่ยวได้ (`tests/`)
- โมเดลถูกโหลด **ครั้งเดียวต่อ process** แล้วใช้ซ้ำทุกเอกสาร
- เรียกโมเดล **2 ครั้งต่อเอกสาร**: อ่านหัวตาราง 1 ครั้ง + อ่านทุกช่องรวมกัน 1 ครั้ง

## 2. แต่ละขั้น

| # | ไฟล์ | รับ → ส่งออก | ทำอะไร (สรุป) |
|---|---|---|---|
| 1 | `image_loader.py` | path → ภาพ BGR | ตรวจไฟล์, ถอดรหัส (JPEG ธรรมดาใช้ OpenCV; ภาพที่มี EXIF หมุน/PNG/อื่นๆ ใช้ Pillow), จัดการ EXIF |
| 2 | `layout.py` (`auto`, default) | ภาพ → ตารางที่ยืดตรง + ตำแหน่งเส้น | หาเส้นจากหมึกพิมพ์ (adaptive threshold) → แก้เอียง → หากรอบผู้สมัคร → fit เส้นขอบ 4 ด้านด้วย Hough (2 รอบ) → ยืดตรงกว้าง 1360 px → ตรวจว่าเป็นตารางจริง → ปรับแสงให้เรียบ → อ่านตำแหน่งเส้นแถว/คอลัมน์ |
| 2 | `alignment.py` (`template`) | ภาพ → ตารางที่ยืดตรงตามพิกัด template | ทางเลือกสำหรับฟอร์มที่รู้พิกัดแน่นอน (`changhouse_v1/v2.yaml`) |
| 2 | `table_detector.py` | ภาพ → mask เส้นตาราง | ใช้ร่วมกันทั้งสองโหมด: mask หมึกพิมพ์, morphology หาเส้นยาว, projection |
| 3 | `layout.py → locate_qty_column` | ตาราง → index คอลัมน์ qty | อ่านบรรทัดแรกของหัวคอลัมน์หาคำว่า `qty` / `จำนวน`; ไม่เจอ → คอลัมน์ที่ 2 จากขวา |
| 4 | `roi_extractor.py` | ตาราง + index → crop ทุกแถว | ตัดระหว่างเส้นแล้วหดเข้า 4 px, ตรวจขนาด |
| 5 | `blank_detector.py` | crop → ว่าง/มี/ไม่แน่ใจ + mask + จำนวนกลุ่มหมึก | วัดหมึกเทียบสีกระดาษในช่องนั้น (ใช้ได้กับปากกาทุกสี) |
| 6 | `preprocessing.py` | crop → ภาพสำหรับโมเดล | `tight_crop` (ภาพหลัก), `digit_segments` (แยกทีละหลัก); variant อื่นมีไว้ทดลอง ปิดอยู่ |
| 7 | `recognizer.py`, `digit_decoder.py`, `device.py` | ภาพ → ข้อความ + score | เรียกโมเดล, ดึง probability จาก paddlex (`post_op` hook), ถอดใหม่เป็นตัวเลข 0–9, หาค่ากรณีเขียนติดกัน (CTC Viterbi) |
| 8 | `postprocessing.py` | ผลการอ่าน → value + status + เหตุผล | ตรวจรูปแบบตัวเลข, กติกาตัดสิน — รายละเอียดทั้งหมดใน [`DECISION_LOGIC.md`](DECISION_LOGIC.md) |
| — | `exporter.py`, `visualization.py` | ผล → ไฟล์ | JSON, CSV (UTF-8 BOM เปิด Excel ได้), summary.md, overlay, contact sheet |
| — | `evaluation.py`, `experiments.py` | ผล + เฉลย → ตัวเลขวัดผล | exact match, CER, ความถูกต้องของช่องว่าง; ปฏิเสธเฉลยที่ยังไม่ `verified` |
| — | `config.py`, `schemas.py`, `net.py`, `cli.py` | — | config + ตรวจค่า, โครงสร้างข้อมูล, บังคับ IPv4, คำสั่ง CLI |

## 3. ข้อตกลงที่ใช้ทั้งระบบ

- **ภาพเป็น BGR uint8** (แบบ OpenCV) ทุกขั้น — `image_loader` แปลงให้ตั้งแต่ต้น
- **กรอบ (bbox)** = `[x_min, y_min, x_max, y_max]` เป็นจำนวนเต็ม, `x_max/y_max` ไม่รวม (slice `img[y0:y1, x0:x1]` ได้ตรงๆ)
- **ระบบพิกัด 2 แบบ**:
  - *aligned* = ภาพตารางที่ยืดตรงแล้ว (โหมด auto: กว้าง 1360 px + ขอบ 12 px; โหมด template: ขนาดภาพ template)
  - *original* = ภาพต้นฉบับ — `H` แปลง original→aligned, `H_inv` แปลงกลับ
  - ผลแต่ละช่องเก็บทั้ง `bbox_aligned` และ `bbox_original`
- **ค่า qty เป็น string** (`"007"` เก็บเลข 0 นำหน้า) และ `value_int` แยกให้; ช่องว่าง = `null` ไม่ใช่ `"0"`
- **ทุกค่าตั้งอยู่ใน YAML** และถูกตรวจตอนเริ่ม (`config.py`) — key ผิด/ค่าผิด → error ทันที ไม่มีค่าตายตัวซ่อนในโค้ด

## 4. โมเดลและ engine

- โมเดล: `PP-OCRv5_server_rec` (ระบุชื่อตายตัวเสมอ — ค่า default ของ PaddleOCR 3.7 คือ PP-OCRv6)
- engine default: `onnxruntime` + ไฟล์ `PP-OCRv5_server_rec_onnx` (weights เดียวกันที่ PaddlePaddle export) — เร็วกว่า Paddle ~2.9 เท่า ผลตรงกัน
- engine สำรอง: `paddle_static` (ตั้ง `ocr.engine`)
- **digit-constrained decoding** ต้องอ่าน probability ภายในของ paddlex (`predictor.post_op`) ซึ่งไม่ใช่ API ทางการ
  → ตรวจโครงสร้างตอนเริ่ม ถ้า paddlex เปลี่ยนจะ error ทันที (ล็อก `paddlex==3.7.2`) ปิดได้ด้วย `ocr.digit_constrained_decoding: false`
- โมเดลไม่ได้อยู่ในโปรเจกต์ — ดาวน์โหลดอัตโนมัติไป `~/.paddlex/official_models/` (เหตุผลดู README หัวข้อ 3)

## 5. Device (CPU / GPU)

`device.py`: `hardware.device` = `cpu` | `auto` | `gpu` | `gpu:N`
1. ตรวจว่า engine ที่เลือกใช้ CUDA ได้จริง (onnxruntime: มี `CUDAExecutionProvider`; paddle: build CUDA + เห็นการ์ด)
2. `auto` → ใช้ GPU ถ้าได้ ไม่งั้น CPU; `gpu` แต่ใช้ไม่ได้ → error
3. หลังโหลดโมเดล ตรวจ provider ที่ ONNX Runtime ใช้จริง — ถ้าขอ GPU แต่ได้ CPU (ถอยเงียบๆ) → error

เส้นทาง GPU เตรียมไว้แต่ **ยังไม่ได้ทดสอบบน GPU จริง** (README หัวข้อ 11)

## 6. การทำงานแบบ batch

| วิธี | ทำงานอย่างไร | ใช้เมื่อ |
|---|---|---|
| ปกติ | 1 process โหลดโมเดลครั้งเดียว ทำทีละเอกสาร | ค่า default |
| `--workers N` | N process แต่ละตัวโหลดโมเดลเอง (~0.75 GB/ตัว) ผลเรียงตามลำดับไฟล์เดิม | ภาพหลายสิบใบขึ้นไป (2 workers เร็วขึ้น ~25%) |
| `--prefetch` | เตรียมเอกสารถัดไปใน thread ระหว่างอ่านเอกสารปัจจุบัน | แทบไม่ช่วยบน M5 (CPU เต็มอยู่แล้ว) — ปิดไว้ |

ทุกวิธีให้ผลเหมือนกันทุกช่อง (มี test ยืนยัน)

## 7. เครือข่ายและ offline

- `network.force_ipv4: true` — เครื่องพัฒนาใช้ IPv6 ไม่ได้ ถ้าไม่บังคับ IPv4 การดาวน์โหลดจะค้างเงียบ
- `network.disable_model_source_check: true` — ไม่ให้ PaddleX เช็คเน็ตตอนเริ่ม
- เมื่อมีโมเดลใน cache แล้ว **ไม่มีการเชื่อมต่อเน็ตเลย** (ทดสอบโดยบล็อก socket — `test_runs_fully_offline`)
- ย้าย cache ได้ด้วย `PADDLE_PDX_CACHE_HOME` หรือชี้โฟลเดอร์โมเดลด้วย `ocr.model_dir`
