# Handwritten Qty OCR

ระบบอ่านตัวเลขลายมือในคอลัมน์ `qty` ของใบสั่งสินค้า CHANGHOUSE แล้วส่งออกผลเป็น JSON และ CSV พร้อมระบุช่องที่ต้องตรวจซ้ำ

ระบบทำงานในเครื่องทั้งหมด: ไม่ส่งภาพไปยัง cloud API. ใช้ PP-OCRv5 ผ่าน ONNX Runtime และรองรับทั้งภาพสแกนกับภาพถ่ายของฟอร์มที่มีตาราง

> สถานะ: prototype ที่พร้อมใช้งานภายในงานที่มี human review; ยังไม่ใช่ระบบตัดสินข้อมูลอัตโนมัติแบบ production

## เริ่มต้น

ต้องใช้ Python 3.11 บน macOS และ Homebrew

```bash
brew install python@3.11
cd handwritten-qty-ocr
bash scripts/setup_mac.sh
source .venv/bin/activate

python scripts/check_environment.py
python -m pytest -q
```

เมื่อ `check_environment.py` รายงาน `RESULT: READY` ให้รัน OCR กับภาพตัวอย่างได้ทันที

```bash
python -m qty_ocr.cli run \
  --input data/samples/order_form_01.jpg \
  --output outputs/example \
  --debug
```

เปิด `outputs/example/qty_overlay.png` เพื่อตรวจตำแหน่งช่อง และเปิด `results.csv` เพื่อใช้งานต่อใน Excel

## คำสั่งหลัก

```bash
# ตรวจตารางและ crop โดยไม่โหลดโมเดล
python -m qty_ocr.cli crop --input INPUT.jpg --output outputs/crops

# อ่านภาพเดียว
python -m qty_ocr.cli run --input INPUT.jpg --output outputs/run

# อ่านทุกภาพในโฟลเดอร์
python -m qty_ocr.cli batch --input-dir data/incoming --output outputs/batch --workers 2

# วัดผลกับ ground truth ที่ยืนยันแล้ว
# document_id ในผลลัพธ์ต้องตรงกับ key ใน ground truth
python -m qty_ocr.cli evaluate \
  --predictions outputs/DOCUMENT_ID/results.json \
  --ground-truth path/to/verified-ground-truth.json
```

เพิ่ม `--debug` เมื่อต้องการภาพประกอบการตรวจสอบ. ผลลัพธ์ใน `outputs/` สร้างใหม่ได้และไม่ถูกเก็บใน Git

## ผลลัพธ์

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `results.json` | ผลครบถ้วนสำหรับระบบอื่น |
| `results.csv` | ผลระดับแถวสำหรับ Excel หรือการตรวจโดยคน |
| `summary.md` | สรุปสถานะและรายการที่ต้องตรวจ |
| `qty_overlay.png` | ภาพต้นฉบับพร้อมตำแหน่งและผลอ่าน |
| `crops/` | ภาพที่โมเดลใช้ อ่านเฉพาะเมื่อเปิด `--debug` |

ให้ถือ `needs_review` และ `invalid_text` เป็นงานของผู้ตรวจเสมอ; `ok` หมายถึงผ่านกฎตรวจปัจจุบัน ไม่ใช่การรับประกันความถูกต้อง

## โครงสร้างโปรเจกต์

| ตำแหน่ง | เนื้อหา |
|---|---|
| `src/qty_ocr/` | pipeline, การอ่านภาพ, OCR, กฎตัดสิน และ export |
| `configs/` | ค่า layout, OCR และเกณฑ์ review |
| `scripts/` | ติดตั้ง, ตรวจ environment, profile และเครื่องมือสำหรับทดสอบ |
| `tests/` | ชุดทดสอบ pytest |
| `data/samples/` | ภาพตัวอย่างสำหรับเริ่มต้น |
| `data/ground_truth/` | ตัวอย่างและข้อมูลอ้างอิงสำหรับการประเมิน |
| `docs/` | เอกสารสำหรับผู้พัฒนาและผู้ดูแลระบบ |

## เอกสารประกอบ

| เอกสาร | อ่านเมื่อ |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | ต้องแก้หรือเพิ่มส่วนของ pipeline |
| [Decision logic](docs/DECISION_LOGIC.md) | ต้องเข้าใจสถานะและเหตุผลที่ระบบขอ review |
| [Validation](docs/BENCHMARK.md) | ต้องทดสอบหรือรายงานผลหลังแก้ระบบ |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | ติดตั้งไม่ผ่าน, โหลดโมเดลไม่ได้, หรือหา table ไม่เจอ |

## ทำงานต่ออย่างปลอดภัย

1. เริ่มจาก `configs/changhouse.yaml` และ `src/qty_ocr/pipeline.py`
2. เพิ่มหรือแก้พฤติกรรมพร้อม test ที่ `tests/`
3. รัน `python -m pytest -q` ก่อน commit
4. ใช้ ground truth ที่มนุษย์ยืนยันแล้วก่อนปรับ threshold หรือเคลมความแม่นยำ

## GPU (NVIDIA)

เส้นทาง GPU ยังไม่ได้ validate บนเครื่อง production. บน Linux ใช้ `bash scripts/setup_gpu.sh`; บน Windows ใช้ `scripts/setup_gpu.ps1`. หลังติดตั้ง ให้รัน `python scripts/check_environment.py` และทดสอบภาพตัวอย่างด้วย `--device gpu` ก่อนใช้งานจริง. หาก CUDA ใช้ไม่ได้ ระบบจะ error แทนการ fallback เป็น CPU

## ข้อจำกัด

- ออกแบบสำหรับฟอร์มที่มีตารางและหัวคอลัมน์ qty; ฟอร์มใหม่ควรตรวจ overlay ก่อนใช้จริง
- ความแม่นยำขึ้นกับลายมือ, แสง, มุมภาพ และคุณภาพเส้นตาราง
- NVIDIA GPU มี config และสคริปต์ติดตั้ง แต่ยังต้อง validate บนเครื่องเป้าหมายก่อนใช้งานจริง
