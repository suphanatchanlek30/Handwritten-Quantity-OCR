# Handwritten Quantity OCR

[![Tests](https://github.com/suphanatchanlek30/Handwritten-Quantity-OCR/actions/workflows/test.yml/badge.svg)](https://github.com/suphanatchanlek30/Handwritten-Quantity-OCR/actions/workflows/test.yml)

OCR สำหรับอ่านตัวเลขลายมือในคอลัมน์ `qty` ของเอกสารที่มีตาราง เช่น ใบสั่งสินค้า ระบบทำงานในเครื่องทั้งหมด ไม่อัปโหลดภาพไปยัง cloud API และส่งออกผลเป็น JSON/CSV พร้อมระบุช่องที่ควรให้คนตรวจซ้ำ

ใช้ **PP-OCRv5_server_rec** ผ่าน ONNX Runtime เป็นค่าเริ่มต้น รองรับภาพสแกนและภาพถ่ายมือถือที่เห็นเส้นตารางชัดเจน

> สถานะ: prototype สำหรับ workflow ที่มี human review ไม่ควรใช้สถานะ `ok` เป็นการรับรองความถูกต้องของข้อมูลสำคัญ

## สิ่งที่โปรเจกต์ทำได้

- หาตารางและคอลัมน์ `qty` อัตโนมัติจากภาพ
- แก้ภาพเอียงหรือ perspective เบื้องต้น แล้ว crop แต่ละช่อง
- แยกช่องว่างออกจากลายมือ สร้าง crop ที่เหมาะกับ OCR และอ่านเฉพาะตัวเลข
- เปรียบเทียบการอ่านทั้งก้อนกับการอ่านทีละกลุ่มหมึก เพื่อ flag ค่าที่เสี่ยง
- สร้าง `results.json`, `results.csv`, `summary.md` และ overlay สำหรับตรวจด้วยตา

## เริ่มต้น

### 1. Clone

```bash
git clone https://github.com/suphanatchanlek30/Handwritten-Quantity-OCR.git
cd Handwritten-Quantity-OCR
```

ต้องใช้ Git และ **Python 3.11 แบบ 64-bit**. การดาวน์โหลดโมเดลครั้งแรกใช้พื้นที่ประมาณ 84 MB และต้องใช้อินเทอร์เน็ต

### macOS (Apple silicon)

ต้องมี Homebrew ก่อน แล้วรัน:

```bash
brew install python@3.11
bash scripts/setup_mac.sh
source .venv/bin/activate
```

สคริปต์สร้าง virtual environment, ติดตั้ง dependency ที่ล็อกเวอร์ชัน, ดาวน์โหลดโมเดล และตรวจ environment ให้จบในครั้งเดียว รองรับและทดสอบบน macOS Apple silicon; Intel Mac ยังไม่ได้ validate

### Windows x64 (CPU)

ติดตั้ง [Python 3.11 x64](https://www.python.org/downloads/windows/) โดยเลือก **Add Python to PATH** และ Python Launcher จากนั้นเปิด PowerShell ในโฟลเดอร์โปรเจกต์:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
```

หากไม่ต้องการเปลี่ยน execution policy ของ session ใช้:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

### Windows / Linux with NVIDIA GPU (optional)

สำหรับ GPU NVIDIA ที่มี driver พร้อมแล้ว ใช้ `requirements-gpu.txt` และสคริปต์เฉพาะแพลตฟอร์ม:

```powershell
.\scripts\setup_gpu.ps1
```

```bash
bash scripts/setup_gpu.sh
```

เส้นทาง GPU ยังต้อง validate บนเครื่องเป้าหมายก่อนใช้งานจริง สคริปต์จะหยุดทันทีถ้า CUDA provider ใช้ไม่ได้ แทนที่จะ fallback เป็น CPU แบบเงียบ ๆ

## ตรวจว่าพร้อมใช้งาน

macOS/Linux:

```bash
source .venv/bin/activate
python scripts/check_environment.py
python -m pytest -q
```

Windows:

```powershell
.\.venv\Scripts\python.exe scripts\check_environment.py
.\.venv\Scripts\python.exe -m pytest -q
```

ผลลัพธ์ต้องลงท้ายด้วย `RESULT: READY` และ test ทั้งหมดต้องผ่านก่อนเริ่มแก้ pipeline

## ใช้งาน

```bash
# ตรวจ geometry และ crop โดยไม่โหลด OCR model
python -m qty_ocr.cli crop --input INPUT.jpg --output outputs/crops

# อ่านภาพเดียว; --debug เก็บ overlay และ crop ไว้ตรวจ
python -m qty_ocr.cli run --input INPUT.jpg --output outputs/run --debug

# อ่านทุกภาพในโฟลเดอร์
python -m qty_ocr.cli batch --input-dir data/incoming --output outputs/batch --workers 2

# วัดผลจาก ground truth ที่มนุษย์ยืนยันแล้ว
python -m qty_ocr.cli evaluate \
  --predictions outputs/run/results.json \
  --ground-truth data/ground_truth/annotations.user_confirmed.json
```

บน Windows ให้เปลี่ยน `python` เป็น `.\.venv\Scripts\python.exe` และใช้ `\` เป็นตัวคั่น path

## Pipeline ทำงานอย่างไร

```text
input image
  -> normalize orientation and load as BGR
  -> detect table, deskew, and correct perspective
  -> locate the qty column and crop its cells
  -> detect blank / handwriting ink in each cell
  -> make tight crops and optional per-digit segments
  -> PP-OCRv5 recognition with digit-constrained decoding
  -> validate candidates and flag uncertainty
  -> JSON / CSV / summary / debug overlay
```

1. **Geometry** — หาเส้นตาราง, ปรับภาพให้ตารางตรง และเลือกคอลัมน์ `qty` จากหัวตาราง; ถ้าอ่านหัวไม่ได้จะใช้ตำแหน่งสำรองที่กำหนดใน config
2. **Cell preparation** — ตัดขอบเส้นตารางออก, แยก blank/ink และ normalize ภาพ เพื่อไม่ให้เงาหรือพื้นกระดาษรบกวน OCR
3. **Recognition** — อ่าน tight crop เป็นหลัก และเมื่อหมึกแยกเป็นหลายกลุ่มจะอ่านทีละกลุ่มเป็นหลักฐานเพิ่ม
4. **Decision** — รับเฉพาะคำตอบตัวเลขที่ผ่านจำนวนหลักและกฎ confidence; ความขัดแย้ง, คะแนนต่ำ หรือหลักที่อาจหาย จะเป็น `needs_review`
5. **Reviewable output** — ผลลัพธ์เก็บค่าที่เสนอ, confidence, เหตุผล และ crop/overlay เพื่อให้คนตรวจย้อนกลับได้

ดูรายละเอียดของ contract ระหว่างแต่ละขั้นที่ [Architecture](docs/ARCHITECTURE.md) และความหมายของสถานะที่ [Decision logic](docs/DECISION_LOGIC.md)

## ผลลัพธ์

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `results.json` | ข้อมูลผลเต็มสำหรับระบบอื่น |
| `results.csv` | ผลระดับแถว เปิดใน Excel หรือส่งให้ผู้ตรวจ |
| `summary.md` | รายการช่องที่ระบบขอ review |
| `qty_overlay.png`, `contact_sheet.png` | ภาพตรวจสอบที่สร้างเมื่อใช้ `--debug` |
| `crops/` | ภาพที่โมเดลอ่านจริง; ค่า default ของ `run` เก็บไว้, ส่วน `batch` เก็บเมื่อใช้ `--debug` |

`needs_review`, `invalid_text`, `blank` และ `alignment_failed` ต้องมี workflow ให้คนตรวจเสมอ

## โครงสร้างโปรเจกต์

| ตำแหน่ง | เนื้อหา |
|---|---|
| `src/qty_ocr/` | pipeline, image processing, OCR, decision policy และ export |
| `configs/` | ค่า table detection, OCR และ review policy |
| `scripts/` | setup, environment checks, profiling และเครื่องมือทดลอง |
| `tests/` | unit/integration tests ที่รันได้โดยไม่ต้องโหลดโมเดล |
| `data/samples/` | ตัวอย่างที่ commit ไว้เพื่อทดลอง |
| `data/ground_truth/` | labels สำหรับประเมินผล; ใช้เฉพาะชุดที่ verified เมื่อต้องรายงานความแม่นยำ |
| `outputs/` | ผลที่สร้างใหม่ได้ จึงไม่เก็บใน Git |

## ดูแลโปรเจกต์อย่างปลอดภัย

- อย่า commit เอกสารลูกค้าจริง, model weights, virtual environment หรือ `outputs/`; `.gitignore` จัดการไว้แล้ว
- เก็บภาพตัวอย่างที่แชร์ได้ใน `data/samples/`; วางข้อมูลจริงที่เป็นความลับไว้ใน `data/private/` หรือ `data/incoming/`
- ปรับ threshold หรือ preprocessing ได้เมื่อมี labels ที่มนุษย์ยืนยันแล้วเท่านั้น
- เพิ่ม regression test สำหรับทุก bug หรือรูปแบบเอกสารใหม่ก่อนปรับ pipeline

## เอกสารประกอบ

| เอกสาร | อ่านเมื่อ |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | ต้องแก้หรือเพิ่มส่วนของ pipeline |
| [Decision logic](docs/DECISION_LOGIC.md) | ต้องเข้าใจสถานะและเหตุผลที่ระบบขอ review |
| [Validation](docs/BENCHMARK.md) | ต้องทดสอบหรือรายงานผลหลังแก้ระบบ |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | ติดตั้งไม่ผ่าน, โหลดโมเดลไม่ได้, หรือหา table ไม่เจอ |

## ข้อจำกัด

- ออกแบบสำหรับเอกสารที่มีตารางและหัวคอลัมน์ qty ไม่ใช่ OCR ตัวเลขทั่วไปทุกแบบ
- ความแม่นยำขึ้นกับลายมือ, แสง, มุมกล้อง และความสมบูรณ์ของเส้นตาราง
- ตัวเลข performance หรือ accuracy ต้องรายงานพร้อมชุดข้อมูล, config และสถานะการยืนยัน label เสมอ
