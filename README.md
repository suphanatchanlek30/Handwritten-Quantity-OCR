# Handwritten Qty OCR — อ่านตัวเลขลายมือในช่อง `qty` ของใบสั่งสินค้า CHANGHOUSE

ระบบอ่าน **ตัวเลขที่เขียนด้วยมือในคอลัมน์ `qty`** ของใบสั่งสินค้า แล้วส่งออกเป็น JSON / CSV พร้อมบอกว่าช่องไหนต้องให้คนตรวจ
ทำงาน **ในเครื่องทั้งหมด** บน MacBook (Apple Silicon, CPU) — ไม่ใช้ cloud API, ไม่ส่งภาพออกนอกเครื่อง

- โมเดลอ่านตัวอักษร: `PP-OCRv5_server_rec` (PaddleOCR 3.x, weights ทางการ) รันด้วย **ONNX Runtime**
- หาตาราง / คอลัมน์ / แถวเองอัตโนมัติ — ใช้ได้ทั้งภาพสแกน ภาพถ่ายมือถือ และฟอร์มที่เพิ่ม/ย้ายคอลัมน์
- ความเร็ว ~0.6 วินาที/เอกสาร, RAM ~0.7 GB

> **สถานะ:** prototype ที่ใช้งานได้จริง ยังไม่ใช่ production
> ภาพสแกน 21 ใบ: ถูก 205/210 ช่อง และ**ไม่มีช่องที่ผิดแต่ระบบบอกว่า `ok`** — ช่องที่ผิดถูก flag ให้คนตรวจทั้งหมด
> ยังไม่เคยทดสอบ**ใบสั่งสินค้า**ที่ถ่ายด้วยมือถือจริง (ทดสอบแค่ภาพจำลอง) — มีภาพถ่ายจริงที่เป็นกระดาษเปล่าเขียนตัวเลข 4 หน้า: ลายมือชัดถูก 98–99%, ลายมือที่ 4/2/8 คล้าย 9 ถูก 64–77%
> (ดู [อ่านหน้ากระดาษเปล่าที่มีตัวเลขหลายตัว](#อ่านหน้ากระดาษเปล่าที่มีตัวเลขหลายตัว-scriptsgrid_page_ocrpy)) — ดูหัวข้อ [ข้อจำกัด](#10-ข้อจำกัด-และสิ่งที่ยังไม่ได้ทำ)

---

## สารบัญ

1. [เริ่มต้นเร็ว (5 นาที)](#1-เริ่มต้นเร็ว)
2. [โครงสร้างไฟล์ทั้งหมด](#2-โครงสร้างไฟล์ทั้งหมด)
3. [ทำไมไม่มีไฟล์โมเดลในโปรเจกต์](#3-ทำไมไม่มีไฟล์โมเดลในโปรเจกต์)
4. [ไฟล์ที่ไม่ได้อยู่ในโฟลเดอร์นี้ (ต้องรู้)](#4-ไฟล์ที่ไม่ได้อยู่ในโฟลเดอร์นี้)
5. [คำสั่งทั้งหมด](#5-คำสั่งทั้งหมด)
6. [อ่านผลลัพธ์](#6-อ่านผลลัพธ์)
7. [ระบบทำงานอย่างไร](#7-ระบบทำงานอย่างไร)
8. [ปรับค่า (config)](#8-ปรับค่า-config)
9. [สำหรับคนที่มาทำต่อ](#9-สำหรับคนที่มาทำต่อ)
10. [ข้อจำกัด และสิ่งที่ยังไม่ได้ทำ](#10-ข้อจำกัด-และสิ่งที่ยังไม่ได้ทำ)
11. [รันบน GPU (NVIDIA)](#11-รันบน-gpu-nvidia)

### เอกสารทั้งหมด

| เอกสาร | อ่านเมื่อ |
|---|---|
| **README.md** (ไฟล์นี้) | เริ่มต้น, ติดตั้ง, ใช้งาน, โครงสร้างไฟล์ |
| [`docs/DECISION_LOGIC.md`](docs/DECISION_LOGIC.md) | ★ ระบบตรวจอะไร ใช้ค่าเท่าไหร่ เมื่อไหร่ต้องรีวิว และคนรีวิวควรดูอะไร |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | โครงสร้างระบบ, แต่ละโมดูลทำอะไร, ข้อตกลงที่ใช้ทั้งระบบ |
| [`docs/BENCHMARK.md`](docs/BENCHMARK.md) | ผลการทดลองจริงทั้งหมด + สิ่งที่ลองแล้วไม่ได้ผล |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | เจอปัญหา — จัดตามอาการ |
| [`docs/COST_ESTIMATE.md`](docs/COST_ESTIMATE.md) | spec ขั้นต่ำ, CPU vs GPU ไหวกี่รูป, ค่าเช่า cloud, ค่าใช้จ่ายต่อรูป เทียบกับ ChatGPT/Gemini |
| [`PLAN.md`](PLAN.md) | ประวัติการพัฒนาทีละขั้น (M0–M9) |

---

## 1. เริ่มต้นเร็ว

ต้องมี Homebrew และ **Python 3.11** (สำคัญ: `python3` ของเครื่องนี้คือ 3.15 ซึ่ง PaddlePaddle ไม่รองรับ)

```bash
brew install python@3.11
cd handwritten-qty-ocr
bash scripts/setup_mac.sh                 # สร้าง .venv + ติดตั้งทุกอย่าง + ดาวน์โหลดโมเดล (ครั้งแรกต้องมีเน็ต)
source .venv/bin/activate

python scripts/check_environment.py       # ต้องจบด้วย RESULT: READY
python -m qty_ocr.cli run --input data/samples/order_form_01.jpg --output outputs/run_001 --debug
```

ดูผล: เปิด `outputs/run_001/qty_overlay.png` (กรอบสีบนภาพจริง) และ `outputs/run_001/results.csv` (เปิดด้วย Excel ได้)

<details>
<summary>ติดตั้งเองทีละขั้น (แทน setup_mac.sh)</summary>

```bash
/opt/homebrew/bin/python3.11 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements.txt
python -m pip uninstall -y opencv-python opencv-python-headless   # กัน cv2 ซ้อนกัน 2 ตัว
python -m pip install -e . --no-deps
python scripts/check_environment.py --download
```
</details>

เวอร์ชันที่ทดสอบแล้ว: macOS 27 arm64 (MacBook Air M5 16 GB), Python 3.11.17, paddlepaddle 3.3.0, paddleocr 3.7.0,
paddlex 3.7.2, onnxruntime 1.31.0, opencv-contrib-python 4.10.0.84, numpy 2.3.5 (ล็อกไว้ใน `requirements.txt`)

---

## 2. โครงสร้างไฟล์ทั้งหมด

```text
handwritten-qty-ocr/
│
├── README.md                    ← ไฟล์นี้
├── PLAN.md                      แผนงาน/ประวัติการพัฒนา (milestone M0–M8) + ข้อเท็จจริงที่ตรวจแล้วของ environment
├── pyproject.toml               นิยาม package `qty_ocr` (ติดตั้งแบบ `pip install -e .`)
├── requirements.txt             เวอร์ชัน dependency ที่ตรวจแล้ว (ล็อกเวอร์ชันทุกตัว) — Mac / CPU
├── requirements-gpu.txt         สำหรับเครื่อง NVIDIA GPU (Linux/Windows) — เตรียมไว้ ยังไม่ได้ทดสอบบน GPU จริง
├── .gitignore                   ไม่เอา .venv/, outputs/, cache ต่างๆ เข้า git
│
├── configs/                     ค่าตั้งทั้งหมด (ไม่มีค่าตายตัวซ่อนในโค้ด)
│   ├── changhouse.yaml          ★ config หลัก (ค่า default) — layout: auto ใช้ได้ทุกฟอร์ม
│   ├── changhouse_v1.yaml       โหมด template: พิกัดตายตัวของฟอร์มเดิม (1667×1759, 4 คอลัมน์)
│   └── changhouse_v2.yaml       โหมด template: พิกัดตายตัวของฟอร์มใหม่ (2591×3452, มีคอลัมน์ No.)
│
├── src/qty_ocr/                 ★ โค้ดหลัก (Python package) — เรียงตามลำดับที่ข้อมูลไหลผ่าน
│   ├── cli.py                   จุดเริ่ม: คำสั่ง run / crop / batch / evaluate / experiment
│   ├── config.py                อ่าน + ตรวจ YAML (key ผิด/ค่าผิด → error ตั้งแต่เริ่ม)
│   ├── pipeline.py              ★ ร้อยทุกขั้นเข้าด้วยกัน: process_document(), process_many(), --workers
│   ├── image_loader.py          [1] โหลดภาพ, EXIF, ตรวจไฟล์เสีย → BGR
│   ├── layout.py                [2] หาตารางแบบอัตโนมัติ (โหมด auto): ยืดตรง, หาแถว/คอลัมน์, อ่านหัวตาราง "qty"
│   ├── alignment.py             [2] หาตารางแบบ template (โหมด template) + ฟังก์ชันเรขาคณิตที่ใช้ร่วมกัน
│   ├── table_detector.py        [2] หาเส้นตารางจากหมึกพิมพ์ (morphology, adaptive threshold)
│   ├── roi_extractor.py         [3] ตัด crop ช่อง qty ทีละแถว
│   ├── blank_detector.py        [4] ช่องว่าง / มีลายมือ / ไม่แน่ใจ + แยกกลุ่มหมึกทีละหลัก
│   ├── preprocessing.py         [5] สร้างภาพสำหรับอ่าน: tight_crop, digit_segments (+ variant ทดลอง)
│   ├── recognizer.py            [6] เรียกโมเดล PP-OCRv5 (โหลดครั้งเดียว) + hook ดึง probability
│   ├── digit_decoder.py         [6] ถอดผลใหม่ให้ออกแค่ 0–9 + ตรวจตัวเลขที่เขียนติดกัน (CTC Viterbi)
│   ├── postprocessing.py        [7] ตรวจว่าเป็นตัวเลขจริง + กติกาตัดสินค่า + เหตุผลที่ต้อง review
│   ├── schemas.py               โครงสร้างข้อมูลผลลัพธ์ (FieldResult, DocumentResult, สถานะต่างๆ)
│   ├── exporter.py              เขียน results.json / results.csv / summary.md
│   ├── visualization.py         ภาพ debug: overlay, contact sheet, เส้นตาราง
│   ├── evaluation.py            วัดความแม่นยำเทียบ ground truth (ปฏิเสธถ้า GT ยังไม่ verified)
│   ├── experiments.py           ทดลองเทียบวิธี preprocessing E1–E7
│   ├── device.py                เลือก CPU / GPU (cpu, auto, gpu:N) + กันไม่ให้ถอยไป CPU เงียบๆ
│   └── net.py                   บังคับ IPv4 + ปิดการเช็คเน็ตของ PaddleX
│
├── scripts/                     เครื่องมือเสริม (ไม่ใช่ส่วนของ pipeline)
│   ├── setup_mac.sh             ติดตั้งทั้งหมดบน Mac (บังคับ Python 3.11)
│   ├── setup_gpu.sh             ติดตั้งบน Linux + NVIDIA GPU (ยังไม่ได้ทดสอบ)
│   ├── setup_gpu.ps1            ติดตั้งบน Windows + NVIDIA GPU (ยังไม่ได้ทดสอบ)
│   ├── check_environment.py     ตรวจ Python/arm64/package/โมเดล → READY หรือไม่
│   ├── smoke_test_ocr.py        ทดสอบโมเดลกับ crop เดียว (data/samples/qty_sample.png)
│   ├── profile_pipeline.py      วัดเวลาแต่ละขั้น, จำนวนครั้งที่เรียกโมเดล, RAM (+ บันทึกผลไว้เทียบ)
│   ├── compare_results.py       ★ เทียบผลสองชุดทีละช่อง — ใช้ทุกครั้งที่แก้โค้ด (ดูหัวข้อ 9)
│   ├── benchmark.py             วัดเวลาตาม batch size / threads (รุ่นเก่า; ใช้ profile_pipeline แทนได้)
│   ├── simulate_photos.py       สร้างภาพถ่ายมือถือจำลอง (เอียง/บิด/เงา/เบลอ) ไว้ทดสอบ
│   └── grid_page_ocr.py         ตัดตัวเลขทุกตัวจากหน้ากระดาษเปล่า (ไม่มีตาราง) → อ่านด้วยโมเดล + ภาพสรุปทุกตัว (ดูหัวข้อ 6)
│
├── tests/                       pytest 134 tests — รันด้วย `python -m pytest -q` (~10 วินาที)
│   ├── conftest.py              ฟอร์มสังเคราะห์สำหรับทดสอบ + fixture config
│   ├── test_layout.py           หาตารางอัตโนมัติ: ฟอร์มเพิ่มคอลัมน์, ภาพถ่ายจำลอง, เส้นจุดไข่ปลา
│   ├── test_alignment.py        โหมด template: หมุน/บิด/ย่อขยาย
│   ├── test_roi_extractor.py    crop อยู่ในคอลัมน์ qty เท่านั้น (ไม่อ่านตัวเลขนอกตาราง)
│   ├── test_blank_detector.py   ช่องว่าง vs เลข 0 vs เส้นบาง, หมึกทุกสี, แยกทีละหลัก
│   ├── test_digit_decoder.py    ถอดผลแบบจำกัดตัวเลข + ตัวเลขติดกัน
│   ├── test_postprocessing.py   กติกาตัดสินค่า, leading zero, ไม่แปลง O→0
│   ├── test_pipeline.py         ทั้ง pipeline + รันโมเดลจริงกับภาพตัวอย่าง
│   ├── test_performance_paths.py  ทางลัดที่เพิ่มความเร็วต้องให้ผลเหมือนเดิม + รัน offline ได้
│   └── test_device.py           เลือก CPU/GPU + กันการถอยไป CPU เงียบๆ (จำลอง GPU ด้วย fake — รันได้ไม่ต้องมี GPU)
│
├── data/
│   ├── samples/
│   │   ├── order_form_01.jpg    ภาพตัวอย่างหลัก (สำเนาของ ../Data Test/arm-1.jpg)
│   │   └── qty_sample.png       crop ช่องเดียวสำหรับ smoke test
│   ├── simulated_photos/        42 ภาพถ่ายจำลองที่สร้างจาก ../Data Test (19 MB, สร้างใหม่ได้)
│   └── ground_truth/            ค่าเฉลยสำหรับวัดผล
│       ├── annotations.user_confirmed.json  ✔ example.jpg — ผู้ใช้ยืนยันค่าแล้ว (verified)
│       ├── annotations.draft.json           ✎ arm-1..20 + example — agent ถอดเอง, ยังไม่มีคนตรวจ
│       ├── real_verified-2.csv              ✔ เฉลยจริงจากเจ้าของ: IMG_9328 (writer data1, 150 ตัว) + หน้า Mind (154 ตัว)
│       ├── toey.claude_draft.csv            ✎ หน้า toey 150 ตัว — Claude อ่านเอง (status claude_draft) ยังไม่มีเจ้าของตรวจ
│       ├── annotations-2.csv, labels_to_fill-2.csv  สำเนาไฟล์เดียวกับ real_verified-2.csv (เนื้อหาเหมือนกันทุกไบต์)
│       ├── IMG_9328.claude_reading_unverified.json  ✎ หน้ากระดาษเปล่า 150 ตัว — agent อ่านเอง, ไม่ใช่เฉลย (ใช้ real_verified-2.csv แทน)
│       └── annotations.example.json         ตัวอย่าง format เท่านั้น (ค่าสมมติ)
│
├── docs/
│   ├── DECISION_LOGIC.md        ★ เกณฑ์ตัดสินทุกด่าน + ค่าที่ใช้ + เหตุผลรีวิวทั้งหมด + ตัวอย่างจริง
│   ├── ARCHITECTURE.md          โครงสร้างระบบ, หน้าที่ของแต่ละโมดูล, ข้อตกลงพิกัด/ข้อมูล
│   ├── BENCHMARK.md             ผลการทดลองทุกครั้ง (ตัวเลขจริง) + สิ่งที่ลองแล้วไม่ได้ผล
│   └── TROUBLESHOOTING.md       ปัญหาที่เจอบ่อยและวิธีแก้ (จัดตามอาการ)
│
├── outputs/                     ผลการรัน (ไม่อยู่ใน git, ลบได้ ยกเว้น baseline — ดูด้านล่าง)
└── .venv/                       Python environment (~1 GB, ไม่อยู่ใน git, สร้างใหม่ด้วย setup_mac.sh)
```

### โฟลเดอร์ใน `outputs/` อันไหนสำคัญ

| โฟลเดอร์ | คืออะไร | ลบได้ไหม |
|---|---|---|
| `baseline_scan/`, `baseline_photo/` | **ผลอ้างอิง** ก่อนการปรับความเร็ว — ใช้กับ `compare_results.py` | ❌ เก็บไว้ |
| `final_scan/`, `final_photo/`, `profiles/` | ผล + ตัวเลขเวลาของเวอร์ชันปัจจุบัน | เก็บไว้ (อ้างอิงใน BENCHMARK) |
| `run_001/`, `example_test/`, `crop_test/` | ตัวอย่างผลพร้อมภาพ debug | ลบได้ |
| `batch_v*/`, `experiment_v*/`, `*_old/`, `sim_photos_final/` | ประวัติการทดลองแต่ละรอบ | ลบได้ |

---

## 3. ทำไมไม่มีไฟล์โมเดลในโปรเจกต์

**สั้นๆ:** โมเดลไม่ได้เป็นของที่เราสร้าง — เป็น weights ทางการของ PaddlePaddle ที่ **ดาวน์โหลดอัตโนมัติครั้งแรกที่รัน**
แล้วเก็บไว้ใน cache กลางของเครื่อง (`~/.paddlex/official_models/`) ไม่ใช่ในโฟลเดอร์โปรเจกต์

| เหตุผล | อธิบาย |
|---|---|
| **ไม่ได้แก้หรือเทรนโมเดล** | ใช้ weights ทางการตรงๆ ทุกบิต — ไม่มีไฟล์โมเดลที่เป็นของโปรเจกต์นี้โดยเฉพาะ (เคยเริ่ม fine-tune แต่ยกเลิกและลบไปแล้ว) |
| **ระบุโมเดลด้วยชื่อที่ตายตัว** | โค้ดเรียก `model_name="PP-OCRv5_server_rec"` เสมอ (ห้ามใช้ค่า default ของ library ซึ่งตอนนี้เป็น PP-OCRv6) → ทุกเครื่องได้โมเดลเดียวกัน |
| **ไฟล์ใหญ่** | ~81 MB ต่อโมเดล — ไม่เหมาะกับ git และ PaddleX จัดการดาวน์โหลด/ตรวจไฟล์ให้เองอยู่แล้ว |
| **ใช้ร่วมกันได้** | cache กลางใช้ร่วมกับทุกโปรเจกต์ในเครื่อง ไม่ต้องเก็บซ้ำ |
| **license ชัดเจน** | Apache-2.0 จาก PaddlePaddle — แหล่งต้นทางคือ Hugging Face (ลิงก์ด้านล่าง) |

### โมเดลอยู่ที่ไหน และใช้ตัวไหน

| โฟลเดอร์ใน `~/.paddlex/official_models/` | ขนาด | ใช้เมื่อ | แหล่งที่มา |
|---|---|---|---|
| `PP-OCRv5_server_rec_onnx/` (`inference.onnx`, `inference.yml`) | 81 MB | ★ **ค่า default** (`ocr.engine: onnxruntime`) | [PaddlePaddle/PP-OCRv5_server_rec_onnx](https://huggingface.co/PaddlePaddle/PP-OCRv5_server_rec_onnx) |
| `PP-OCRv5_server_rec/` (`inference.json`, `inference.pdiparams`, ...) | 81 MB | `ocr.engine: paddle_static` (ช้ากว่า ~2.9 เท่า, ผลตรงกัน) | [PaddlePaddle/PP-OCRv5_server_rec](https://huggingface.co/PaddlePaddle/PP-OCRv5_server_rec) |

ทั้งสองเป็น **โมเดลเดียวกัน weights เดียวกัน** — ตัว ONNX คือการ export ทางการจาก PaddlePaddle
เราตรวจแล้วว่าให้ผลตรงกันทุกช่องบน 63 ภาพ (score ต่างไม่เกิน 4e-5) ดู `docs/BENCHMARK.md` หัวข้อ 3

### วิธีได้โมเดลมา

- **อัตโนมัติ (ปกติ):** `bash scripts/setup_mac.sh` หรือ `python scripts/check_environment.py --download` — ดาวน์โหลดตัวที่ config ใช้
- **หลังจากดาวน์โหลดแล้ว ทำงาน offline 100%** (ทดสอบโดยบล็อกเน็ตทั้งหมดแล้ว — มี test `test_runs_fully_offline`)
- **เครื่องที่ไม่มีเน็ต:** copy โฟลเดอร์ทั้งสองจาก `~/.paddlex/official_models/` ของเครื่องที่มีแล้วไปไว้ที่เดียวกัน
  หรือชี้ cache ไปที่อื่นด้วย `export PADDLE_PDX_CACHE_HOME=/path/to/cache` หรือตั้ง `ocr.model_dir` ใน config
- **ดาวน์โหลดเอง:**
  ```bash
  python -c "from qty_ocr.net import force_ipv4; force_ipv4(); import os; \
  from huggingface_hub import snapshot_download; \
  snapshot_download('PaddlePaddle/PP-OCRv5_server_rec_onnx', local_dir=os.path.expanduser('~/.paddlex/official_models/PP-OCRv5_server_rec_onnx'))"
  ```

> ⚠️ **เครื่องนี้ IPv6 ใช้ไม่ได้** — ถ้าไม่บังคับ IPv4 การดาวน์โหลดจะค้างเงียบ (CPU 0%) ไม่มี error
> config ตั้ง `network.force_ipv4: true` ไว้แล้ว ถ้าเขียนสคริปต์เองให้เรียก `qty_ocr.net.force_ipv4()` ก่อน

---

## 4. ไฟล์ที่ไม่ได้อยู่ในโฟลเดอร์นี้

| อะไร | อยู่ที่ไหน | ใช้ทำอะไร |
|---|---|---|
| ภาพทดสอบ 20 ใบ (`arm-1.jpg` … `arm-20.jpg`) | `../Data Test/` (โฟลเดอร์ข้างๆ โปรเจกต์) | วัดผล, batch, สร้างภาพจำลอง |
| ภาพฟอร์มใหม่ (มีคอลัมน์ No.) | `../Data Test/test/example.jpg` | ทดสอบฟอร์มคนละแบบ — ค่าเฉลยยืนยันโดยผู้ใช้แล้ว |
| ภาพถ่ายมือถือจริง: กระดาษเปล่าเขียนตัวเลข 150 ตัว (ถ่ายตะแคง) | `../Data Test/test-1-page/IMG_9328.jpg` | ทดสอบ `scripts/grid_page_ocr.py` — เฉลยจริงอยู่ใน `data/ground_truth/real_verified-2.csv` (writer `data1`) |
| ภาพถ่ายมือถือจริง: กระดาษเปล่า ปากกาน้ำเงิน 150 ตัว (ตั้งตรง) | `../Data Test/test-1-page/S__30957572.jpg` | ทดสอบ `scripts/grid_page_ocr.py` — ยังไม่มีเฉลย |
| ภาพถ่ายมือถือจริง: กระดาษแนวนอน 11 × 14 = 154 ตัว | `../Data Test/test-1-page/Mind.jpg` | เฉลยจริงใน `real_verified-2.csv` (writer `Mind`) |
| ภาพถ่ายมือถือจริง: กระดาษเปล่า 150 ตัว (ตั้งตรง) | `../Data Test/test-1-page/toey.jpg` | เฉลยร่างโดย Claude: `data/ground_truth/toey.claude_draft.csv` |
| โมเดล | `~/.paddlex/official_models/` | ดูหัวข้อ 3 |
| Python environment | `.venv/` (ในโปรเจกต์แต่ไม่ควร copy ข้ามเครื่อง) | สร้างใหม่ด้วย `setup_mac.sh` |

- ถ้าย้ายโปรเจกต์ไปเครื่องอื่น ให้ copy `../Data Test/` ไปด้วย (วางข้างโปรเจกต์ชื่อเดิม) ไม่อย่างนั้น
  test บางตัวจะถูก skip และคำสั่งตัวอย่างที่อ้าง `../Data Test` จะหาไฟล์ไม่เจอ
- โฟลเดอร์ `../EasyOCR`, `../PaddleOCR`, `../Tesseract` ข้างๆ เป็นโฟลเดอร์ว่าง **ไม่เกี่ยวกับโปรเจกต์นี้**
- โค้ดอยู่ใน GitHub (private): `https://github.com/suphanatchanlek30/POC-OCR-PP-OCRv5-server`
  — ใน repo **ไม่มี** `.venv/`, โมเดล (`~/.paddlex`), และภาพทดสอบ `../Data Test/` (อยู่นอกโฟลเดอร์โปรเจกต์)
  มีเฉพาะผลอ้างอิงใน `outputs/baseline_*`, `outputs/final_*`, `outputs/profiles/` สำหรับ `compare_results.py`

---

## 5. คำสั่งทั้งหมด

ทุกคำสั่งรันจากโฟลเดอร์โปรเจกต์ หลัง `source .venv/bin/activate` — ไม่ต้องใส่ `--config` (ใช้ `configs/changhouse.yaml`)

| คำสั่ง | ใช้ทำอะไร |
|---|---|
| `python -m qty_ocr.cli run --input IMG --output DIR --debug` | อ่านเอกสารเดียว + ภาพ debug ครบ |
| `python -m qty_ocr.cli batch --input-dir FOLDER --output DIR` | ทุกภาพในโฟลเดอร์ → แยกโฟลเดอร์ต่อภาพ + `batch_results.csv` รวม |
| `... batch ... --workers 2` | ขนาน 2 process เร็วขึ้น ~25% (RAM รวม ~1.5 GB) — คุ้มเมื่อมีหลายสิบภาพ |
| `... batch ... --debug` | เขียนภาพ debug + crop ด้วย (ค่า default ของ batch ปิดไว้เพื่อความเร็ว) |
| `python -m qty_ocr.cli crop --input IMG --output DIR --debug` | หาตาราง + ตัด crop โดย**ไม่โหลดโมเดล** (เช็คเรขาคณิตเร็วๆ; คอลัมน์ qty ใช้ "ที่ 2 จากขวา") |
| `python -m qty_ocr.cli evaluate --predictions DIR/*/results.json --ground-truth data/ground_truth/annotations.user_confirmed.json` | วัดความแม่นยำ (ทำงานเฉพาะกับ GT ที่ `"verified": true`) |
| `python -m qty_ocr.cli experiment --input IMG... --output DIR` | เทียบวิธี preprocessing E1–E7 |
| `python scripts/check_environment.py` | ตรวจว่าเครื่องพร้อม |
| `python scripts/profile_pipeline.py --inputs FOLDER --repeat 3` | วัดเวลาแต่ละขั้น / RAM |
| `python scripts/compare_results.py OLD_DIR NEW_DIR` | เทียบผลสองชุดทีละช่อง (exit 0 = เหมือนกัน) |
| `python scripts/simulate_photos.py --input "../Data Test" --output data/simulated_photos` | สร้างภาพถ่ายจำลองใหม่ |
| `python scripts/grid_page_ocr.py --input "../Data Test/test-1-page/IMG_9328.jpg" --output outputs/IMG_9328_grid --cols 10 --rows 15 --gt-csv data/ground_truth/real_verified-2.csv --gt-writer data1` | หน้ากระดาษเปล่าที่เขียนตัวเลขหลายตัว: ตัดทีละตัว → อ่าน → ภาพสรุปทุกตัว (ดูหัวข้อ 6) |
| `... run/batch ... --device gpu` | ใช้ NVIDIA GPU (ดูหัวข้อ 11); `--device auto` = ใช้ GPU ถ้ามี |
| `python -m pytest -q` | รัน tests ทั้งหมด |

---

## 6. อ่านผลลัพธ์

```text
outputs/run_001/
  results.csv         ★ เปิดด้วย Excel (UTF-8 BOM): document_id, row_id, qty, confidence, status, needs_review, review_reasons, ...
  results.json        ผลเต็ม: value, raw_text (ผลดิบก่อนจำกัดตัวเลข), confidence, status, review_reasons, ผลของทุกวิธี, กรอบพิกัด
  summary.md          ตารางสรุป + เวลาแต่ละขั้น
  diagnostics.json    ข้อมูลการหาตาราง, สถิติหมึกต่อแถว, เวลา
  qty_overlay.png     ★ กรอบบนภาพจริง: เขียว=ok  เหลือง=ต้องตรวจ  เทา=ว่าง  แดง=error
  contact_sheet.png   ★ ทุกแถวในภาพเดียว: crop | ภาพที่ใช้อ่าน | ผล
  aligned.png, aligned_grid.png, table_lines.png, ...    ภาพแต่ละขั้นของการหาตาราง (--debug)
  crops/  masks/      crop และ mask หมึกของแต่ละแถว (--debug)
```

| ค่า | ความหมาย |
|---|---|
| `status: ok` | อ่านได้และไม่มีเหตุให้สงสัย |
| `status: needs_review` | มีค่า แต่ควรให้คนดู — ดู `review_reasons` |
| `status: blank` | ช่องว่าง → `value: null` (**ไม่ใช่ `"0"`**; เลข 0 ที่เขียนจริงได้ `"0"`) |
| `status: invalid_text` / `recognition_error` / `alignment_failed` | อ่านไม่ได้ / โมเดล error / หาตารางไม่เจอ (ระบบไม่เดาค่า) |
| `value` | เป็น string เก็บเลข 0 นำหน้าได้ (`"007"`); `value_int` แยกไว้ |
| `confidence` | ความมั่นใจของโมเดล — **ไม่ใช่ความแม่นยำ** |

เหตุผลรีวิวที่เจอบ่อย (ความถี่บนภาพสแกน 126 ช่องที่มีลายมือ):

| เหตุผล | เกิดเมื่อ | พบ |
|---|---|---:|
| `low_confidence(0.649<0.85)` | ความมั่นใจ < 0.85 | 27 |
| `possible_merged_digits(7->79)` | ตัวเลขเขียนติดกัน ระบบเพิ่มหลักให้ | 7 |
| `letters_mapped_to_digits('BZ'->32)` | โมเดลเห็นเป็นตัวอักษร ระบบแปลงเป็นตัวเลข | 7 |
| `tight_vs_segments_disagree(23 vs 93)` | อ่านทั้งก้อนกับทีละหลักได้ต่างกัน | 4 |

**เกณฑ์ทุกข้อ ค่าที่ใช้ ลำดับการตัดสิน และสิ่งที่คนรีวิวควรดู → [`docs/DECISION_LOGIC.md`](docs/DECISION_LOGIC.md)**

**แก้ผลด้วยมือ:** แก้คอลัมน์ `qty` ใน `results.csv` แล้ว *Save As* เป็นไฟล์ใหม่ เช่น `results.corrected.csv`
อย่าเขียนทับ `results.json` — เก็บผลจากโมเดลไว้ตรวจสอบย้อนหลัง

### อ่านหน้ากระดาษเปล่าที่มีตัวเลขหลายตัว (`scripts/grid_page_ocr.py`)

ใช้กับหน้าที่เขียนตัวเลขเรียงเป็นแถว/คอลัมน์บนกระดาษเปล่า **ไม่มีเส้นตาราง** (ไม่ใช่ใบสั่งสินค้า) เช่น `../Data Test/test-1-page/IMG_9328.jpg`

ขั้นตอน:
1. หมุนภาพให้ตั้งตรง (`--rotate cw|ccw|180|none`, ค่า default `cw`) แล้ว**ย่อ/ขยายให้กว้าง 2160 px** (`--work-width`)
   — ค่าขนาดทุกอย่างในสคริปต์ตั้งไว้ที่ความกว้างนี้ ภาพจากมือถือความละเอียดไหนก็ได้ผลเหมือนกัน
2. หากระดาษ (convex hull ของส่วนที่สว่าง ไม่มีสี) → ตัดพื้นโต๊ะทิ้ง
3. **ปรับแสงให้กระดาษขาว** (หารแต่ละสีด้วยพื้นหลังที่ blur) → ลบเงามือ / แสงไม่เท่ากัน
4. หาหมึก → รวมหลักของตัวเลขเดียวกันเป็นก้อน (ตัดรอยจุดที่เตี้ยกว่า 0.4 เท่าของความสูงปกติทิ้ง)
   → **จัดแถวโดยไล่จากตัวเลขหนึ่งไปตัวถัดไปทางซ้าย/ขวา** โดยคาดตำแหน่งจากความเอียงของแถวนั้นเอง
   (แถวที่เขียนด้วยมือเอียง บางแถวเบียดกัน และคอลัมน์เลื่อนไปมา — ทั้งการเรียงตาม y ทั้งหน้าและการจัดกลุ่มคอลัมน์ตาม x ใช้ไม่ได้)
   — ถ้าแถวไหนมีตัวเลขไม่เท่า `--cols` หรือจำนวนแถวไม่เท่า `--rows` จะเตือน
5. แต่ละตัวผ่านขั้นเดียวกับ pipeline หลัก: `detect_blank` → `tight_crop` (+ `digit_segments` เมื่อมี ≥ 2 กลุ่มหมึก)
   → PP-OCRv5 (ONNX, ถอดเฉพาะ 0–9) → `postprocessing.decide` (กู้เลขที่ติดกัน, เทียบกับการอ่านทีละหลัก, เหตุผลรีวิว)

ผลลัพธ์ (ใน `--output`):

```text
sheet_1..N.png      ★ ทุกตัวเลข (5 แถว/แผ่น): ภาพที่ส่งเข้าโมเดลจริง + ภาพทีละหลัก + คำตอบ (score)
                       เขียว=ok  ส้ม=ควรตรวจ  บรรทัด "Claude:" = ค่าที่ agent อ่านเอง (แดงเมื่อไม่ตรง)
                       (เมื่อใส่ --gt-csv: เขียว=ถูก แดง=ผิด + บรรทัด GT / correct-WRONG / ok-REVIEW)
overlay.jpg         ★ ทั้งหน้า: กรอบรอบตัวเลข + คำตอบเหนือแต่ละตัว + ป้าย rXcY
overlay_gt.jpg      (--gt-csv) ทั้งหน้า: เขียว=ถูก แดง=ผิด, ค่าจริงอยู่ใต้กรอบ
accuracy.md         (--gt-csv) ความแม่นยำ, ช่องที่ผิดแต่ได้ ok, แยกตามจำนวนหลัก, รายการช่องที่ผิดทั้งหมด
                       เฉลยที่ status ไม่ใช่ verified ต้องใส่ --allow-draft-gt และทุกไฟล์จะติดป้าย DRAFT GT
results.csv         1 แถวต่อตัวเลข: value, status, confidence, review_reasons, ผล tight/segments, ... + คอลัมน์ gt / correct
results.json        ผลเต็มทุกตัว
summary.md          สรุป + ตารางตัวที่ต้องตรวจพร้อมเหตุผล
crops/              ภาพที่ส่งเข้าโมเดลจริง (rRR_cCC.png, rRR_cCC_segK.png)
```

**วัดกับเฉลยจริง:** ใส่ `--gt-csv data/ground_truth/real_verified-2.csv --gt-writer data1` ระบบจะเพิ่ม
`overlay_gt.jpg` (เขียว=ถูก, แดง=ผิด, ใต้กรอบคือค่าจริง), `accuracy.md` และคอลัมน์ `gt`/`correct` ใน `results.csv`
(เฉลยนับลำดับจากซ้ายไปขวา บนลงล่าง ใช้เฉพาะแถวที่ `status = verified`)

ผลบน `IMG_9328.jpg` (150 ตัว, 2026-10-15) เทียบกับเฉลยจริงจากเจ้าของ (`real_verified-2.csv`, writer `data1`):

| ตัวชี้วัด | ผล |
|---|---|
| **อ่านถูกทั้งตัวเลข** | **96/150 = 64.0%** |
| อ่านถูกรายหลัก (1 − CER) | 283/347 = 81.6% |
| สถานะ `ok` | 55 ตัว — ถูก 50 (90.9%) |
| สถานะ `needs_review` | 95 ตัว — ถูก 46 (48.4%) |
| **ผิดแต่ได้ `ok`** | **5** (r1c1 20→70, r1c5 790→740, r9c3 949→948, r13c1 974→474, r13c7 381→321) |
| ถ้าคนแก้ทุกช่องที่ระบบเตือน | 145/150 = 96.7% |

| ขั้น | ถูก |
|---|---:|
| ตัดจากภาพถ่ายตรงๆ | 26.0% |
| + ปรับแสงให้กระดาษขาว | 55.3% |
| + ขั้นตัดสินของ pipeline หลัก (digit_segments + decide) | 64.0% |

สาเหตุผิดหลัก: ผู้เขียนเขียน **เลข 4 คล้าย 9** (40→90, 474→974), เลข 2 มีห่วง, เลข 1 ติดกับเลขข้างๆ (21→2)
ทดลองบนภาพนี้ภาพเดียว (in-sample) — ใน CSV ยังมีเฉลยของอีกหน้า (writer `Mind`, 154 ตัว) ที่ยังไม่ได้รัน

ภาพที่ 2: `../Data Test/test-1-page/S__30957572.jpg` (ตั้งตรง, ปากกาน้ำเงิน, กว้าง 1096 px, 15 × 10 ตัว) — **ยังไม่มีเฉลย**

```bash
python scripts/grid_page_ocr.py --input "../Data Test/test-1-page/S__30957572.jpg" --output outputs/S__30957572_grid --rotate none --cols 10 --rows 15
```

ตัดได้ครบ 150 ตัว, `ok` 92 / `needs_review` 58 — แถว 1–9 เขียนเรียง 10…99 จึงเทียบกับลำดับนั้นได้ (**เฉลยสันนิษฐาน ไม่ใช่เฉลยที่ยืนยัน**):
ถูก 69/90 = 76.7%, ผิดแต่ได้ `ok` 6 ตัว — ทั้งหมดเป็น **เลข 2 ที่เขียนคล้าย 9** (22→99, 25→95, 32→39, 42→49, 62→69, 97→94)

ภาพที่ 3: `../Data Test/test-1-page/Mind.jpg` (แนวนอน, 11 × 14 = 154 ตัว) — เทียบ**เฉลยจริง** (`real_verified-2.csv`, writer `Mind`):

```bash
python scripts/grid_page_ocr.py --input "../Data Test/test-1-page/Mind.jpg" --output outputs/Mind_grid --rotate none --cols 14 --rows 11 --gt-csv data/ground_truth/real_verified-2.csv --gt-writer Mind
```

**ถูก 151/154 = 98.1%**, `ok` 142 ตัวถูกทั้งหมด, ผิดแต่ได้ `ok` 0 — 3 ช่องที่ผิด (210→270, 260→210, 750→75) ถูก flag ทั้งหมด
และทุกช่องมีวิธีอ่านอย่างใดอย่างหนึ่ง (ทั้งก้อน / ทีละหลัก) ที่ได้ค่าถูก

ภาพที่ 4: `../Data Test/test-1-page/toey.jpg` (15 × 10 = 150 ตัว) — เทียบ**เฉลยร่างที่ Claude อ่านเอง** (`toey.claude_draft.csv`, ยังไม่มีเจ้าของตรวจ):

```bash
python scripts/grid_page_ocr.py --input "../Data Test/test-1-page/toey.jpg" --output outputs/toey_grid --rotate none --cols 10 --rows 15 --gt-csv data/ground_truth/toey.claude_draft.csv --allow-draft-gt
```

ถูก 149/150 = 99.3% (เฉลยร่าง), `ok` 135 ตัวถูกทั้งหมด, ผิดแต่ได้ `ok` 0 — ช่องเดียวที่ผิดคือ "89." (มีจุดปากกาต่อท้าย) อ่านเป็น 899 และถูก flag

| หน้า | ถูก | ผิดแต่ได้ `ok` | เฉลย |
|---|---|---|---|
| toey | 99.3% | 0 | ร่างโดย Claude |
| Mind | 98.1% | 0 | จริง (verified) |
| S__30957572 | ~76.7% (แถว 1–9) | 6 | สันนิษฐานจากลำดับ 10…99 |
| IMG_9328 | 64.0% | 5 | จริง (verified) |

ความต่างมาจาก**ลายมือ**เป็นหลัก: หน้าที่เขียนตัวเลขแยกชัดได้ 98–99% ส่วนหน้าที่เขียน 4/2/8 คล้าย 9 ลดลงมาก และมีช่องที่ผิดแต่ได้ `ok`
ลองเพิ่ม padding / บังคับความกว้างขั้นต่ำแล้ว แย่ลง → ใช้ `tight_crop_padding_ratio: 0.35` เดิม

---

## 7. ระบบทำงานอย่างไร

```text
ภาพ ─▶ [1] โหลดภาพ ─▶ [2] หาตาราง ─▶ [3] ตัดช่อง qty ─▶ [4] ว่างไหม? ──ว่าง──▶ null
                                                         │
                                                       มีลายมือ
                                                         ▼
       [7] ตัดสินค่า + เหตุผล review ◀─ [6] โมเดลอ่าน ◀─ [5] เตรียมภาพ
                 │
                 ▼
       results.json / results.csv / ภาพ debug
```

| ขั้น | ไฟล์ | ทำอะไร |
|---|---|---|
| 2 หาตาราง | `layout.py` | หาเส้นตารางจาก**หมึกพิมพ์เท่านั้น** (เลขที่เขียนด้วยปากกาสีไม่ถูกนับเป็นเส้น) → แก้ภาพเอียง → หากรอบตารางจริง (ตัดเส้นจุดไข่ปลา/ขอบกระดาษ) → ยืดให้ตรง → ปรับแสง → นับแถว/คอลัมน์จากเส้นจริง → อ่านหัวตารางหาคำว่า `qty` |
| 4 ช่องว่าง | `blank_detector.py` | ตรวจหมึกเทียบสีกระดาษในช่องนั้น (ใช้ได้กับปากกาทุกสี แดง/น้ำเงิน/ดำ/ส้ม) |
| 5 เตรียมภาพ | `preprocessing.py` | `tight_crop` = ตัดรอบหมึกพอดี (ภาพหลัก) + `digit_segments` = แยกทีละหลัก (อ่านเทียบ) |
| 6 อ่าน | `recognizer.py`, `digit_decoder.py` | โมเดลอ่าน → **บังคับให้ผลเป็นตัวเลข 0–9** จาก probability เดิม (ไม่งั้น `32` จะออกมาเป็น `BZ`) → ตรวจตัวเลขที่เขียนติดกัน (`79` ที่ถูกอ่านเป็น `7`) |
| 7 ตัดสิน | `postprocessing.py` | ใช้ผล tight_crop เป็นหลัก เทียบกับผลแยกทีละหลัก ถ้าไม่ตรง/ไม่มั่นใจ → `needs_review` |

กติกาการตัดสินผลแบบละเอียด (ด่านตรวจทุกด่าน, เกณฑ์ตัวเลข, ตัวอย่างจริงทีละขั้น) → [`docs/DECISION_LOGIC.md`](docs/DECISION_LOGIC.md)
โครงสร้างโมดูล → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · ตัวเลขการทดลองที่รองรับการออกแบบ → [`docs/BENCHMARK.md`](docs/BENCHMARK.md)

---

## 8. ปรับค่า (config)

ทุกค่าอยู่ใน `configs/changhouse.yaml` พร้อมคอมเมนต์ภาษาไทย ตรวจความถูกต้องตอนเริ่มโปรแกรม (พิมพ์ key ผิด → error ทันที)

| Section | ค่าที่น่าจะต้องแตะ |
|---|---|
| `ocr` | `engine` (onnxruntime / paddle_static), `confidence_review_threshold` (0.85 — ยังไม่ได้ calibrate), `missing_digit_max_penalty` |
| `layout` | `mode` (auto / template), `qty_header_keywords` (`qty`, `จำนวน`), `qty_column_from_right` (2) |
| `blank_detection` | `dark_min_contrast`, `color_min_contrast` — ถ้าลายมือจางมากแล้วถูกมองว่าช่องว่าง |
| `field` | `max_digits` (3) |
| `hardware` | `device`: `cpu` (default บน Mac) / `auto` / `gpu` / `gpu:N` |
| `network` | `force_ipv4` (ต้องเป็น true บนเครื่องนี้) |
| `output` | เปิด/ปิดการเขียน crop, ภาพ debug, JSON, CSV |

ฟอร์มใหม่ที่หัวคอลัมน์ไม่ใช่ `qty` → เพิ่มคำใน `layout.qty_header_keywords`

---

## 9. สำหรับคนที่มาทำต่อ

### เริ่มอ่านโค้ดตรงไหน

1. `docs/DECISION_LOGIC.md` — เข้าใจก่อนว่าระบบตัดสินผลอย่างไร (ไม่ต้องอ่านโค้ด)
2. `src/qty_ocr/pipeline.py` → `process_document()` — เห็นทุกขั้นในที่เดียว
3. `src/qty_ocr/postprocessing.py` → `decide()` — กติกาการตัดสินค่า (ตรงกับ DECISION_LOGIC หัวข้อ 5)
4. `src/qty_ocr/layout.py` → `locate_table_auto()` — การหาตาราง (ส่วนที่ซับซ้อนที่สุด)
5. `docs/BENCHMARK.md` หัวข้อ 7 — สิ่งที่ลองแล้วไม่ได้ผล (จะได้ไม่ลองซ้ำ)

### กฎเวลาแก้โค้ด

- **แก้เรื่องความเร็ว/โครงสร้าง (ผลต้องเหมือนเดิม):** รันผลใหม่แล้วเทียบกับ baseline ต้องผ่าน 100%
  ```bash
  python scripts/profile_pipeline.py --inputs "../Data Test" "../Data Test/test/example.jpg" --repeat 1 --save-results outputs/new_scan
  python scripts/compare_results.py outputs/baseline_scan outputs/new_scan     # ต้อง exit 0
  python scripts/profile_pipeline.py --inputs data/simulated_photos --repeat 1 --save-results outputs/new_photo
  python scripts/compare_results.py outputs/baseline_photo outputs/new_photo
  ```
- **แก้เรื่องความแม่นยำ (ผลตั้งใจให้เปลี่ยน):** ดูทุกช่องที่ `compare_results` รายงาน — ต้องไม่มีช่องที่เคยถูกแล้วกลายเป็นผิด
  และต้องไม่มีช่องที่ผิดแต่ได้ `ok` เพิ่มขึ้น; วัดกับ `annotations.user_confirmed.json` ด้วย `evaluate`
- **ห้ามปรับ threshold เพื่อให้ตัวเลขดูดีบนชุดทดสอบเดิม** — ข้อมูลมีน้อย จะ overfit (ตัวเลขใน BENCHMARK เป็น in-sample อยู่แล้ว)
- รัน `python -m pytest -q` ก่อนส่งงานทุกครั้ง

### กับดักที่เจอมาแล้ว

| ปัญหา | วิธีแก้ |
|---|---|
| ดาวน์โหลดโมเดลค้าง (CPU 0%) | IPv6 ของเครื่องใช้ไม่ได้ → `qty_ocr.net.force_ipv4()` |
| `pip install paddlepaddle` ไม่เจอ | ใช้ `/opt/homebrew/bin/python3.11` ไม่ใช่ `python3` (3.15) |
| `cv2` ทำงานแปลกๆ | มี OpenCV 2 ตัวซ้อน → เหลือแค่ `opencv-contrib-python` |
| macOS ไม่มีคำสั่ง `timeout` | ใช้ `gtimeout` (`brew install coreutils`) หรือจับเวลาใน Python |
| zsh ไม่แยกคำในตัวแปร `$ARGS` | ใช้ `${=ARGS}` |
| วัดเวลาแล้วตัวเลขแกว่ง ±15% | MacBook Air ไม่มีพัดลม เครื่องร้อนแล้วช้าลง → วัดสลับ A/B หลายรอบ |
| ภาพถ่ายจริง: โมเดลอ่านเป็น `□` `口` `日` แทนตัวเลข | กระดาษในภาพถ่ายเป็นสีเทา (~170) พอ `tight_crop` เติมขอบขาวจึงกลายเป็น "กล่อง" → ปรับแสงให้กระดาษขาวก่อนตัด (`flatten_illumination` ใน `scripts/grid_page_ocr.py`) |
| อัปเกรด paddlex แล้วเริ่มไม่ได้ | การบังคับผลเป็นตัวเลขใช้ attribute ภายในของ paddlex 3.7.2 → ล็อกเวอร์ชันไว้ หรือปิด `ocr.digit_constrained_decoding` |

รายละเอียดเพิ่ม: `docs/TROUBLESHOOTING.md`

---

## 10. ข้อจำกัด และสิ่งที่ยังไม่ได้ทำ

**ข้อจำกัด**
- รองรับฟอร์มแบบตารางที่มีเส้นครบ และมีหัวคอลัมน์ `qty` (หรือ qty เป็นคอลัมน์ที่ 2 จากขวา)
- อ่านเฉพาะเลข 0–9 ในช่อง qty สูงสุด 3 หลัก
- ใช้โมเดลทางการโดยไม่ได้ fine-tune → ลายมือกำกวมยังอ่านผิด: **เลข 1 หัวงอ** (อ่านเป็น 7), `2` หางยาว, `3` มีห่วงบน
  — ส่วนใหญ่ถูก flag ให้ตรวจ
- ภาพถ่ายทดสอบด้วย**ภาพจำลอง**เท่านั้น: ถูก ~86% และมี 4 ช่องจาก 420 ที่ผิดแต่ได้ `ok` (ภาพเบลอมาก)
- ตัวเลขความแม่นยำส่วนใหญ่เทียบกับค่าเฉลยที่ agent ถอดเอง (ยังไม่มีคนตรวจ) — มีเพียง `example.jpg` ที่ผู้ใช้ยืนยันแล้ว (ถูก 9/10)
- **pipeline หลัก (`qty_ocr.cli run/batch`) ยังไม่มีขั้นปรับแสง** — บนภาพถ่ายจริงที่กระดาษเป็นสีเทา `tight_crop` จะสร้างขอบ "กล่อง"
  ให้โมเดลอ่านผิด (พบจาก `IMG_9328.jpg`: score เฉลี่ย 0.48 → 0.71 เมื่อปรับแสง) ภาพสแกนไม่มีปัญหานี้เพราะกระดาษขาวอยู่แล้ว

**สิ่งที่ยังไม่ได้ทำ (เรียงตามความสำคัญ)**
1. ทดสอบกับ**ภาพถ่ายใบสั่งสินค้าจริง**จากหลายคน หลายมุม — และเพิ่มขั้นปรับแสงเข้า pipeline หลัก
   (ต้องตรวจด้วย `compare_results.py` ว่าผลบนภาพสแกนเดิมไม่เปลี่ยน)
2. ให้คนตรวจ `data/ground_truth/annotations.draft.json` แล้วตั้ง `"verified": true`
   ให้เจ้าของตรวจ `toey.claude_draft.csv` (ถ้าถูกให้เปลี่ยน status เป็น verified) และหาเฉลยของ `S__30957572.jpg`
3. ปรับ `confidence_review_threshold` จากข้อมูลจริงเพื่อลดจำนวนช่องที่ต้อง review (~20%)
4. Fine-tune โมเดลสำหรับเลข 1 หัวงอ — **เริ่มแล้วผู้ใช้ยกเลิก** ไฟล์ที่เกี่ยวข้องลบหมดแล้ว
   ถ้าจะทำต่อ ต้องมีใบสั่งสินค้าจริงที่เขียนเลข 1 หัวงอและเลข 7 ด้วยลายมือจริงก่อน (ตอนนี้มีตัวอย่างจริงแค่ 1 ตัว)
5. หน้าจอ Streamlit สำหรับแก้ผลด้วยมือ (ยังไม่ได้ทำ)

---

## 11. รันบน GPU (NVIDIA)

> ⚠️ **เตรียมโค้ดไว้แล้ว แต่ยังไม่ได้ทดสอบบน GPU จริง** (เครื่องพัฒนาเป็น Mac ไม่มี NVIDIA GPU)
> ส่วนที่ทดสอบแล้ว: การเลือก device, การตรวจ config, error เมื่อไม่มี GPU, และการกันไม่ให้ถอยไป CPU เงียบๆ (จำลองด้วย fake ใน `tests/test_device.py`)
> และยืนยันแล้วว่าการเพิ่มส่วนนี้ไม่ทำให้ผลบน CPU เปลี่ยน (compare ตรง 630/630 field)

### คาดว่าจะเร็วขึ้นเท่าไร (ประมาณการ — ยังไม่ได้วัด)

| ขั้น | Mac M5 (วัดจริง) | RTX 3050 (ประมาณ) |
|---|---:|---:|
| OCR (~13 ภาพ/เอกสาร) | ~300 ms | ~50–100 ms |
| หาตาราง (OpenCV บน CPU — GPU ไม่ช่วย) | ~230 ms | ขึ้นกับ CPU ของเครื่องนั้น |
| รวม | ~0.55–0.6 s/เอกสาร | **~0.3–0.4 s/เอกสาร** |

คุ้มเมื่อ batch หลักร้อย–พันใบ (ใช้คู่กับ `--workers` ให้ CPU ช่วยหาตารางขนานกัน); ทีละใบต่างกันไม่มาก

### ติดตั้ง

ต้องมี: NVIDIA driver รุ่นที่รองรับ CUDA 13 (ตรวจด้วย `nvidia-smi`), Python 3.11
ไม่ต้องลง CUDA Toolkit / cuDNN เอง — `onnxruntime-gpu[cuda,cudnn]` ดึง library ของ NVIDIA มาทาง pip

```bash
# Linux
bash scripts/setup_gpu.sh
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\setup_gpu.ps1
```

- ใช้ `requirements-gpu.txt` (แทน `onnxruntime` ด้วย `onnxruntime-gpu`, **ไม่ต้องลง paddlepaddle** — engine onnxruntime ไม่ได้ใช้ paddle)
- **ห้ามลง `onnxruntime` กับ `onnxruntime-gpu` พร้อมกัน** (ชนกัน)
- โมเดลไฟล์เดียวกัน (`PP-OCRv5_server_rec_onnx`) ใช้ได้ทั้ง CPU และ GPU — ดาวน์โหลดอัตโนมัติเหมือนเดิม
- Windows: ตั้ง `PYTHONUTF8=1` (สคริปต์ตั้งให้แล้ว) กัน error เรื่อง encoding

### ใช้งาน

```bash
python scripts/check_environment.py                       # หัวข้อ "GPU (NVIDIA / CUDA)" ต้องเป็น [OK]
python -m qty_ocr.cli run --input data/samples/order_form_01.jpg --output outputs/gpu_run --device gpu
python -m qty_ocr.cli batch --input-dir FOLDER --output outputs/gpu_batch --device gpu --workers 2
```

หรือตั้งใน config: `hardware.device: gpu` (บังคับ) หรือ `auto` (ใช้ GPU ถ้ามี ไม่งั้น CPU)

ระบบจะ **ไม่ถอยไปใช้ CPU แบบเงียบๆ**: ถ้าขอ `gpu` แต่ไม่มี CUDA หรือ ONNX Runtime โหลด CUDA ไม่ขึ้น
(เช่น cuDNN ไม่ตรงเวอร์ชัน) จะ error พร้อมบอกสาเหตุ — log บรรทัด `Loaded ... on gpu:0 ... providers=['CUDAExecutionProvider', ...]` ยืนยันว่าใช้ GPU จริง

### สิ่งที่ต้องทำครั้งแรกบนเครื่อง GPU (ก่อนใช้จริง)

1. `python -m pytest -q` ต้องผ่านทั้งหมด
2. **ตรวจว่าผลเหมือนบน Mac** — copy `outputs/baseline_scan/` และ `../Data Test/` ไปด้วย แล้ว:
   ```bash
   python scripts/profile_pipeline.py --inputs "../Data Test" "../Data Test/test/example.jpg" --repeat 3 \
       --device gpu --save-results outputs/gpu_scan --json-out outputs/profiles/gpu_scan.json
   python scripts/compare_results.py outputs/baseline_scan outputs/gpu_scan
   ```
   GPU คำนวณทศนิยมต่างจาก CPU เล็กน้อย — ถ้า `value/status` ต่างแม้แต่ช่องเดียว ให้ตรวจช่องนั้นก่อนใช้งาน
3. ลอง `ocr.batch_size` 1 / 8 / 16 บน GPU (บน CPU ค่า >1 ไม่ช่วย แต่บน GPU อาจช่วย) — วัดด้วย `profile_pipeline.py --device gpu --batch-size N` และ compare ทุกครั้ง
4. บันทึกตัวเลขที่วัดได้ลง `docs/BENCHMARK.md`
