# TROUBLESHOOTING — ปัญหาที่เจอบ่อยและวิธีแก้

จัดตามอาการ — เริ่มจาก `python scripts/check_environment.py` ทุกครั้ง (บอกได้ว่าเครื่องพร้อมหรือขาดอะไร)
ดูความหมายของ status / เหตุผลรีวิว → [`DECISION_LOGIC.md`](DECISION_LOGIC.md)

---

## สารบัญ

1. [ติดตั้ง](#1-ติดตั้ง)
2. [ดาวน์โหลด / โหลดโมเดล](#2-ดาวน์โหลด--โหลดโมเดล)
3. [Engine และ GPU](#3-engine-และ-gpu)
4. [หาตารางไม่เจอ / crop ผิดที่](#4-หาตารางไม่เจอ--crop-ผิดที่)
5. [ช่องว่าง / มีลายมือ ผิด](#5-ช่องว่าง--มีลายมือ-ผิด)
6. [ค่าที่อ่านได้ / เหตุผลรีวิว](#6-ค่าที่อ่านได้--เหตุผลรีวิว)
7. [ความเร็ว / หน่วยความจำ](#7-ความเร็ว--หน่วยความจำ)
8. [เครื่องมือและ shell บน Mac](#8-เครื่องมือและ-shell-บน-mac)

---

## 1. ติดตั้ง

**`No matching distribution found for paddlepaddle`**
- Python ผิดเวอร์ชัน — `python3` ของเครื่องนี้คือ 3.15 ซึ่ง Paddle ไม่มี wheel → ใช้ `/opt/homebrew/bin/python3.11`
  (`brew install python@3.11`) แล้วสร้าง venv ใหม่: `rm -rf .venv && bash scripts/setup_mac.sh`
- รันใต้ Rosetta อยู่: `python -c "import platform; print(platform.machine())"` ต้องได้ `arm64`
- ต้องติดตั้งจาก index ของ Paddle: `pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/`
- หมายเหตุ: engine default (onnxruntime) ไม่ได้ใช้ paddle — แต่ `setup_mac.sh` ลงไว้เพื่อให้สลับ engine ได้

**`import cv2` แปลกๆ / function หาย / version ไม่ตรง**
- มี OpenCV 2 ตัวซ้อน (`opencv-python(-headless)` + `opencv-contrib-python` ที่ paddlex ใช้)
- แก้: `pip uninstall -y opencv-python opencv-python-headless && pip install --force-reinstall --no-deps opencv-contrib-python==4.10.0.84`
- ตรวจ: `check_environment.py` → บรรทัด `single OpenCV distribution` ต้อง `[OK]`

**`UserWarning: No ccache found`** — ไม่ใช่ปัญหา (เกี่ยวกับการ compile ของ Paddle ซึ่งไม่ได้ใช้)

---

## 2. ดาวน์โหลด / โหลดโมเดล

**ค้างตอนเริ่มครั้งแรก / `~/.paddlex` ว่าง / CPU 0%**
- สาเหตุที่เจอจริงบนเครื่องนี้: **IPv6 ใช้ไม่ได้** (`curl -6 https://huggingface.co` timeout แต่ `curl -4` ได้ 200)
- แก้: `network.force_ipv4: true` ใน config (ตั้งไว้แล้ว) — สคริปต์ที่เขียนเองให้เรียก `qty_ocr.net.force_ipv4()` ก่อน import อื่น
- ดาวน์โหลดเองล่วงหน้า:
  ```bash
  python -c "from qty_ocr.net import force_ipv4; force_ipv4(); import os; \
  from huggingface_hub import snapshot_download; \
  snapshot_download('PaddlePaddle/PP-OCRv5_server_rec_onnx', local_dir=os.path.expanduser('~/.paddlex/official_models/PP-OCRv5_server_rec_onnx'))"
  ```
  (สำหรับ engine `paddle_static` เปลี่ยนเป็น `PaddlePaddle/PP-OCRv5_server_rec`)
- เปลี่ยนแหล่งดาวน์โหลด: `export PADDLE_PDX_MODEL_SOURCE=modelscope` (หรือ `aistudio`, `bos`)
- เครื่องไม่มีเน็ต: copy โฟลเดอร์จาก `~/.paddlex/official_models/` ของเครื่องอื่นมาไว้ที่เดียวกัน (README หัวข้อ 3)

**log บอกว่าโหลดโมเดลอื่น ไม่ใช่ v5**
- ค่า default ของ `TextRecognition` ใน PaddleOCR 3.7 คือ `PP-OCRv6_medium_rec` — โค้ดนี้ส่ง `model_name="PP-OCRv5_server_rec"` เสมอ
- ตรวจ log บรรทัด `Loaded PP-OCRv5_server_rec ... providers=[...]`

**`RecognizerInitError: digit_constrained_decoding needs paddlex ... post_op.character`**
- paddlex ที่ติดตั้งมีโครงสร้างภายในต่างจาก 3.7.2 ที่ตรวจไว้ (อัปเกรดไปโดยไม่ตั้งใจ)
- แก้: `pip install paddleocr==3.7.0 paddlex==3.7.2` หรือปิดชั่วคราว `ocr.digit_constrained_decoding: false` (ความแม่นยำจะลดลงมาก — BENCHMARK หัวข้อ 5)

---

## 3. Engine และ GPU

**ONNX Runtime (ค่า default)**
- ใช้ไฟล์ `PP-OCRv5_server_rec_onnx` (weights เดียวกับ Paddle, export ทางการ) — ผลตรงกับ Paddle ทุกช่อง เร็วกว่า ~2.9 เท่า
- `import onnxruntime` ไม่ได้ → `pip install onnxruntime==1.31.0`
- กลับไปใช้ Paddle: `ocr.engine: paddle_static` (ช้ากว่า แต่ผลตรงกัน — ตรวจด้วย `compare_results.py`)

**Paddle crash (เฉพาะ `ocr.engine: paddle_static`)**
- ลด `hardware.cpu_threads` เป็น 1–2, `ocr.batch_size: 1`, คง `ocr.enable_mkldnn: false`
- หรือกลับไปใช้ engine `onnxruntime`

**GPU (NVIDIA) — เตรียมไว้ ยังไม่ได้ทดสอบบน GPU จริง**

| ข้อความ error | สาเหตุ | แก้ |
|---|---|---|
| `no usable GPU for engine 'onnxruntime': onnxruntime has no CUDAExecutionProvider` | ลง `onnxruntime` ตัว CPU อยู่ | `pip uninstall -y onnxruntime && pip install -r requirements-gpu.txt` |
| `GPU requested but the ONNX Runtime session runs on ['CPUExecutionProvider']` | ONNX Runtime โหลด CUDA/cuDNN ไม่ขึ้นแล้วถอยไป CPU (ระบบนี้ไม่ยอมรันต่อแบบเงียบๆ) | ตรวจ driver รองรับ CUDA 13 (`nvidia-smi`), ลงใหม่ด้วย `onnxruntime-gpu[cuda,cudnn]`, ดูชื่อไฟล์ `.so`/`.dll` ที่หาไม่เจอใน log |
| `paddlepaddle is a CPU build` | ใช้ `paddle_static` บน GPU แต่ลง paddle ตัว CPU | ลง `paddlepaddle-gpu` ตาม paddlepaddle.org.cn หรือใช้ engine onnxruntime แทน (แนะนำ) |

ใช้งานไปก่อนได้ด้วย `--device cpu` หรือ `hardware.device: auto`

---

## 4. หาตารางไม่เจอ / crop ผิดที่

**`alignment_failed` + `no_table_with_grid_found` (โหมด auto)**
- เปิด `table_lines.png` (เส้นที่ระบบจับได้) และ `detected_table.png` (กรอบที่เลือก) — ต้องรันด้วย `--debug`
- ถ่ายให้เห็นตารางครบ **ทั้ง 4 ขอบ**, เส้นตารางไม่ขาด, ลดมุมเอียง/บิด, หลีกเลี่ยงเงาพาดเส้น
- เส้นตารางจางมาก → ลด `alignment.adaptive_c` (เช่น 8)
- ตารางเล็กในภาพ / เส้นสั้น → ลด `layout.min_table_area_ratio` หรือ `layout.final_line_coverage` (0.7)
- เกณฑ์ทั้งหมดของด่านนี้ → `DECISION_LOGIC.md` หัวข้อ D2

**`alignment_failed` (โหมด template: `changhouse_v1/v2.yaml`)**
- ฟอร์มไม่ตรงพิกัด template → ใช้ `configs/changhouse.yaml` (โหมด auto) แทน
- หรือแก้ `template.vertical_lines` / `horizontal_lines` ให้ตรงฟอร์ม

**เหตุผล `qty_column_by_position` / ผลทั้งเอกสารผิดคอลัมน์**
- อ่านหัวตารางไม่เจอคำว่า qty → ระบบใช้คอลัมน์ที่ 2 จากขวา; ดู `qty_overlay.png` ว่ากรอบอยู่ถูกคอลัมน์ไหม
- ฟอร์มใช้คำอื่น → เพิ่มใน `layout.qty_header_keywords`; คอลัมน์ qty อยู่ตำแหน่งอื่น → แก้ `layout.qty_column_from_right`
- `results.json → alignment.qty_column.header_texts` บอกว่าโมเดลอ่านหัวตารางได้ว่าอะไร

**จำนวนแถวไม่ใช่ 10**
- ดู `results.json → alignment.row_count_note` และ `aligned_grid.png` — เส้นแถวบางเส้นจางเกินไป หรือมีเส้นแปลกปลอม

**crop ตัดขอบตัวเลข**
- ลายมือชนเส้นตาราง → ลด `roi.crop_margin_px` (เช่น 2) — ระวังเศษเส้นตารางหลุดเข้ามา

---

## 5. ช่องว่าง / มีลายมือ ผิด

ดู `masks/row_XX_foreground.png` (หมึกที่ระบบเห็น) และ `diagnostics.json → blank_stats` (จำนวน pixel, ความสูงเส้น)
เกณฑ์ทั้งหมด → `DECISION_LOGIC.md` หัวข้อ F2

**ช่องมีลายมือแต่ได้ `blank`** (ปากกาจางมาก)
- ลด `blank_detection.dark_min_contrast` (เช่น 35) และ/หรือ `color_min_contrast` (เช่น 20)
- เลข 1 สั้นๆ บางๆ → ลด `min_stroke_height_px` หรือ `uncertain_min_pixels`

**ช่องว่างแต่ได้ลายมือ / `blank_detection_uncertain`** (เงา, ฝุ่น, รอยลบ)
- เพิ่ม `nonblank_min_pixels`, `min_component_area`
- เศษเส้นตารางหลุดเข้ามาใน mask → เพิ่ม `blank_detection.inspect_margin_px`

**หมายเหตุ:** ค่า `color_min_saturation` / `dark_max_gray` ใช้เฉพาะเมื่อ `ink_threshold: absolute` (ค่า default คือ `relative`)

---

## 6. ค่าที่อ่านได้ / เหตุผลรีวิว

ความหมายของทุกเหตุผลและสิ่งที่คนรีวิวควรดู → `DECISION_LOGIC.md` หัวข้อ 6 และ 9

| อาการ | คำอธิบาย |
|---|---|
| `letters_mapped_to_digits('BZ'->32)` | โมเดลเห็นเป็นตัวอักษร ระบบเลือกตัวเลขที่ probability สูงสุดแทน — มักถูกแต่เป็นการเดา จึงต้องรีวิว (ไม่มีตารางแปลง O→0, I→1) |
| `possible_merged_digits(7->79)` | ตัวเลขเขียนติดกัน ระบบเพิ่มหลักให้ — ตรวจ **หลักแรก** เป็นพิเศษ (เช่น 1 หัวงอถูกเห็นเป็น 7) |
| `tight_vs_segments_disagree(...)` | อ่านทั้งก้อนกับทีละหลักได้ต่างกัน — ดู `crops/row_XX_seg_K.png` ว่าแยกหลักถูกไหม |
| ผลเปลี่ยนเมื่อถ่ายใหม่/ขยับนิดเดียว | ปกติของโมเดลกับลายมือกำกวม — ค่าที่ไม่มั่นใจถูก flag อยู่แล้ว |
| อยากให้รีวิวน้อยลง | **อย่าลด** `ocr.confidence_review_threshold` โดยไม่มีข้อมูลที่คนตรวจแล้ว — เสี่ยงค่าผิดหลุดเป็น `ok` |
| ลายมือแบบหนึ่งผิดซ้ำๆ (1 หัวงอ, 3 มีห่วง, 2 หางยาว) | ข้อจำกัดของโมเดลที่ไม่ได้ fine-tune — ต้องใช้ตัวอย่างลายมือจริงมา fine-tune (README หัวข้อ 10) |

**แก้ค่าด้วยมือ:** แก้คอลัมน์ `qty` ใน `results.csv` แล้ว Save As เป็นไฟล์ใหม่ — อย่าเขียนทับ `results.json`

---

## 7. ความเร็ว / หน่วยความจำ

| อาการ | แก้ |
|---|---|
| ช้ากว่าที่ BENCHMARK บอก | MacBook Air ไม่มีพัดลม — รันต่อเนื่องนานเครื่องร้อนแล้วช้าลง 10–15%; batch ใช้ `--workers 2` |
| batch ช้าเพราะเขียนไฟล์ | batch ไม่เขียนภาพ debug/crop เป็นค่า default แล้ว — อย่าใส่ `--debug` ถ้าไม่จำเป็น |
| RAM ไม่พอ | แต่ละ worker ใช้ ~0.75 GB — ลด `--workers`; ลด `ocr.onnx_intra_op_threads` ช่วยเรื่องความร้อน |
| อยากรู้ว่าช้าตรงไหน | `python scripts/profile_pipeline.py --inputs FOLDER --repeat 3` แยกเวลาตามขั้น |

---

## 8. เครื่องมือและ shell บน Mac

| ปัญหา | แก้ |
|---|---|
| ไม่มีคำสั่ง `timeout` | `brew install coreutils` แล้วใช้ `gtimeout` หรือจับเวลาใน Python |
| zsh ไม่แยกคำในตัวแปร (`$ARGS` ถูกส่งเป็นก้อนเดียว) | ใช้ `${=ARGS}` |
| path มีช่องว่าง (`Data Test`) | ใส่เครื่องหมายคำพูดเสมอ: `"../Data Test"` |
