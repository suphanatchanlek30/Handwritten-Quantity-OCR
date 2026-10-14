> **ไฟล์นี้คือบันทึกประวัติการพัฒนา** (แผนเดิม + สิ่งที่ทำในแต่ละ milestone) — ไม่ใช่เอกสารใช้งาน
> ภาพรวมปัจจุบันดู `README.md`, เกณฑ์การตัดสินดู `docs/DECISION_LOGIC.md`, ตัวเลขผลดู `docs/BENCHMARK.md`

# PLAN — Handwritten Qty OCR (PP-OCRv5_server_rec)

แผนงานแบบ checklist สำหรับ implement ตาม Master Prompt ทีละ Milestone
ทุกข้อต้องรันจริง/ดูภาพ debug จริงก่อนติ๊ก ห้ามติ๊กจากการคาดเดา

## Verified facts (Milestone 0 — ทดสอบจริงแล้ว 2026-10-14)

| Item | Value |
|---|---|
| Machine | Apple M5, 16 GB, macOS 27.0.1, `arm64` |
| Python | Homebrew `python@3.11` → 3.11.17 (เครื่องมี 3.15 เป็น default → Paddle ไม่มี wheel, **ห้ามใช้ `python3` เฉยๆ**) |
| paddlepaddle | 3.3.0 (CPU index `paddlepaddle.org.cn/packages/stable/cpu/`) |
| paddleocr / paddlex | 3.7.0 / 3.7.2 |
| OpenCV | `opencv-contrib-python==4.10.0.84` (dependency ของ paddlex — **ห้ามลง `opencv-python-headless` ซ้อน** เพราะชน namespace `cv2`) |
| Default model ของ `TextRecognition` | `PP-OCRv6_medium_rec` → **ต้องระบุ `model_name="PP-OCRv5_server_rec"` เสมอ** |
| Init kwargs ที่รองรับจริง | `model_name, model_dir, device, engine ("paddle_static"), engine_config, enable_mkldnn (default True), cpu_threads (default 10), input_shape` |
| Result | `TextRecResult`; ใช้ `res.json["res"]["rec_text"]`, `res.json["res"]["rec_score"]` |
| ndarray input | ต้องเป็น **BGR** (BGR ให้ score เท่ากับ file path 0.64119; RGB ได้ 0.64053) |
| Model cache | `~/.paddlex/official_models/PP-OCRv5_server_rec/` (84 MB) override ได้ด้วย `PADDLE_PDX_CACHE_HOME` |
| Model source | env `PADDLE_PDX_MODEL_SOURCE` (default `huggingface`), `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True` ข้ามการเช็กเน็ต |
| Network | เครื่องนี้ **IPv6 ใช้ไม่ได้** → การดาวน์โหลดค้าง ต้อง force IPv4 (patch `socket.getaddrinfo`) ก่อน import อื่น |
| Smoke result | row 1 ของ `arm-1.jpg` → `"15"`, score 0.641, init 1.1 s, infer ~55 ms |

ข้อสังเกต: score 0.64 ทั้งที่อ่านถูก → threshold 0.85 เป็นแค่สมมติฐานเริ่มต้น จะ flag review บ่อย

## Inputs

- End-to-end target: `Data Test/arm-1.jpg` → copy เป็น `data/samples/order_form_01.jpg`
- Blank-detector check: `Data Test/arm-14.jpg` (เส้นปากกาบางมาก, "11" เป็นเส้นตั้งแดงบางๆ)
- ภาพทั้ง 20 ภาพเป็น digital render 1667×1759 template เดียวกัน → alignment แทบเป็น identity; ต้องทดสอบ alignment ด้วย synthetic rotate/scale/perspective
- ขอบขวานอกตาราง (x≈1520) มีตัวเลขแดงซ้ำค่า qty → **pipeline ห้ามอ่าน** (มี test ยืนยัน) แต่ใช้ให้คนตรวจ ground truth ได้

## Key design decisions (final — ปรับตามผลทดลองจริง)

1. **แยกหมึกก่อนหาเส้นตาราง**: grid mask = gray ≤ 210 & saturation ≤ 60 (เส้นตารางจาง ~160 → 170 ไม่พอ)
2. **Alignment**: deskew (HoughLinesP) → outer quad (เส้นถูก thicken 3 px ให้ทน perspective) → homography
   → **refine ด้วยจุดตัดเส้นทั้งหมด** (แก้ bias ของ quad ที่หนา) → verify ≥ 85% เส้น; ไม่ผ่าน → static fallback (flag) / `alignment_failed`
3. **Blank detection**: ink = saturation ≥ 40 ∪ gray ≤ 170 (ภาพจริงมีหมึกแดง/น้ำเงิน/ดำ/ส้ม) + กฎความสูง stroke สำหรับเลข 1
4. **Variants**: original / grayscale / red_mask (ข้ามถ้าไม่มีหมึกแดง) / ink_isolation (ทุกสี) / tight_crop / adaptive (off)
5. **Decision policy**: `primary_variant: tight_crop` (E5 ตรง draft 92% vs ~48% ของ variant ทั้งช่อง);
   variant อื่นเป็น cross-check (`variant_disagreement` เมื่อ score ≥ 0.85); `ink_groups_exceed_digits`; ไม่ใช้ majority vote
6. **Network**: `qty_ocr.net.force_ipv4()` ผ่าน config `network.force_ipv4`

## Milestones

### M0 — Environment ✅
- [x] `brew install python@3.11`, venv `.venv`
- [x] paddlepaddle 3.3.0, paddleocr 3.7.0 (แก้ OpenCV ซ้อน)
- [x] โหลดโมเดล + smoke test จริง
- [x] `scripts/setup_mac.sh`, `check_environment.py` (READY), `smoke_test_ocr.py`, `benchmark.py`, `requirements.txt`

### M1 — Document geometry ✅
- [x] image_loader / alignment / table_detector / roi_extractor
- [x] `crop` command; 20/20 ภาพจริงเจอเส้นครบ 17/17; ภาพจริงหมุน ±4–7°, perspective, scale → ผ่าน

### M2 — Handwriting preparation ✅
- [x] blank detector: 20 ภาพ → 120/120 nonblank, 80/80 blank (draft)
- [x] preprocessing variants + masks

### M3 — OCR integration ✅
- [x] `PaddleV5Recognizer` (load once, BGR, timing, per-batch errors)
- [x] numeric validation + evidence-based decision policy

### M4 — Structured output ✅
- [x] JSON / CSV (UTF-8 BOM) / summary.md / diagnostics.json / overlay / contact sheet
- [x] CLI `crop`, `run`, `batch`, `evaluate`, `experiment`

### M5 — Tests & docs ✅
- [x] pytest 71 passed ในรอบ v1 (ปัจจุบัน 86 — ดู M6)
- [x] Experiment E1–E6 (v1) → ปัจจุบัน E1–E7 ใน `docs/BENCHMARK.md`
- [x] README (ไทย), ARCHITECTURE, TROUBLESHOOTING
- [x] `annotations.draft.json` (`verified: false`) — **รอคนตรวจ**

### M6 — Accuracy v2 (คำขอเพิ่ม: แยกทีละตัว + ทายแม่นขึ้น โดยไม่ช้าลง) ✅
- [x] Digit-constrained CTC decoding (`digit_decoder.py`, hook `post_op` ตรวจกับ paddlex 3.7.2)
- [x] แยกทีละหลัก (`ink_group_masks` + `digit_segments`) แล้วอ่าน/ต่อกัน
- [x] Experiment E1–E7 + เทียบ policy: 109 → 115/120 ถูก, invalid 5 → 0, 1.75 → 0.97 s/doc
- [x] Draft GT cross-check กับตัวเลขขอบขวา (แก้ 2 ค่า)
- [x] tests 86 passed
- [x] Clean install จริง: copy project (ไม่มี .venv) + model cache ว่าง → `setup_mac.sh` → READY,
      PaddleX ดาวน์โหลดโมเดลเองผ่าน IPv4 (10.6 s), run + pytest ผ่านในสำเนา

### M7 — v3: ตารางยืดหยุ่น + ตัวเลขติดกัน + ภาพถ่าย ✅
- [x] `layout.py`: หาตาราง/คอลัมน์/แถวเองไม่ใช้ template, Hough border fit, ตัดเส้นที่ไม่ต่อกับตาราง, อ่านหัวตาราง `qty`
- [x] adaptive grid threshold, relative ink threshold, flatten illumination
- [x] ตัวเลขเขียนติดกัน: length-constrained CTC Viterbi (`decode_fixed_length`, `extra_digit_penalty`)
- [x] `scripts/simulate_photos.py` + 42 ภาพถ่ายจำลอง; ภาพสแกน 205/210, ภาพถ่ายจำลอง 362/420, 914 ms/doc
- [x] tests 110 passed

### M8 — Performance (ผลต้องเหมือนเดิม 100%) ✅
- [x] baseline + `scripts/compare_results.py` + `scripts/profile_pipeline.py`
- [x] OCR ทั้งเอกสารครั้งเดียว (predict 17 → 2/doc), onnxruntime (OCR 2.9×), Viterbi รอบเดียว, JPEG decode เร็ว
- [x] batch: ไม่เขียน debug/crops เป็น default, `--workers N`, offline 100%
- [x] ภาพสแกน 1,128 → 577 ms/doc, ภาพถ่าย 1,166 → 692 ms/doc, RSS −45%; compare 210/210 + 420/420
- [x] tests 115 passed

### M9 — เตรียมรองรับ NVIDIA GPU (ยังไม่ได้ทดสอบบน GPU จริง) ✅
- [x] `device.py`: cpu / auto / gpu / gpu:N + probe ตาม engine + กันการถอยไป CPU เงียบๆ
- [x] `--device` ใน CLI / profile_pipeline; `check_environment.py` รายงาน GPU
- [x] `requirements-gpu.txt` (onnxruntime-gpu[cuda,cudnn]==1.31.0, ไม่ต้องใช้ paddle), `setup_gpu.sh`, `setup_gpu.ps1`
- [x] tests 134 passed (GPU จำลองด้วย fake); เส้นทาง CPU ผลตรง baseline 630/630 และตรงเวอร์ชันก่อนแบบ strict

### M10 — เอกสาร ✅
- [x] `docs/DECISION_LOGIC.md`: ด่านตรวจทุกด่าน, เกณฑ์ตัวเลข, เหตุผลรีวิว + ความถี่จริง, ตัวอย่างทีละขั้น, คู่มือคนรีวิว
- [x] จัดเอกสารทั้งหมดใหม่ให้ตรงกับโค้ดปัจจุบัน (README, ARCHITECTURE, BENCHMARK, TROUBLESHOOTING)

### เหลือ (manual / future)
- [ ] ทดสอบบนเครื่อง NVIDIA GPU จริง (README หัวข้อ 11 มีขั้นตอน)
- [ ] ทดสอบกับภาพถ่ายมือถือจริง
- [ ] คนตรวจ draft GT แล้วตั้ง `verified: true` → รัน `evaluate`
- [ ] ทดสอบภาพถ่ายมือถือจริง
- [ ] Streamlit UI (optional, ยังไม่ทำ)
- [ ] onnxruntime fallback (config รับได้ แต่ยังไม่ทดสอบ)

## Commands (จาก project root)

```bash
source .venv/bin/activate
python scripts/check_environment.py
python scripts/smoke_test_ocr.py --input data/samples/qty_sample.png
python -m qty_ocr.cli crop --input data/samples/order_form_01.jpg --config configs/changhouse_v1.yaml --output outputs/crop_test --debug
python -m qty_ocr.cli run  --input data/samples/order_form_01.jpg --config configs/changhouse_v1.yaml --output outputs/run_001 --debug
python -m pytest -q
```
