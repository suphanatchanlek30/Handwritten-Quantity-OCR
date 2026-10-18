# Decision logic

ระบบเสนอค่าที่อ่านได้และแยกกรณีเสี่ยงออกให้คนตรวจ ไม่ควรใช้สถานะ `ok` แทนการตรวจรับข้อมูลสำคัญ

```text
valid image -> table found -> qty cell -> ink check -> OCR candidates
-> numeric validation -> candidate selection -> status + review reasons
```

## สถานะ

| สถานะ | ความหมาย | การดำเนินการ |
|---|---|---|
| `ok` | อ่านได้และไม่ติดกฎความเสี่ยง | ใช้ต่อได้ตาม workflow ที่ยอมรับความเสี่ยง |
| `needs_review` | มีคำตอบ แต่มีสัญญาณไม่แน่ใจ | ให้คนตรวจภาพ crop และค่าที่เสนอ |
| `invalid_text` | OCR ไม่ได้ผลลัพธ์ตัวเลขที่ใช้ได้ | ให้คนกรอกหรือแก้ไข |
| `blank` | ไม่พบลายมือในช่อง | ตรวจเฉพาะเมื่อช่องนี้ไม่ควรว่าง |
| `alignment_failed` | หา/ปรับตารางไม่สำเร็จ | ตรวจภาพ, config และรูปแบบฟอร์ม |

## สาเหตุที่พบบ่อยของ `needs_review`

- `low_confidence`: คะแนนของ candidate ต่ำกว่า threshold
- `possible_merged_digits`: มีแนวโน้มว่าตัวเลขติดกันและอาจขาดหลัก
- `tight_vs_segments_disagree`: อ่านภาพเต็มกับภาพแยกหลักได้คนละค่า
- `letters_mapped_to_digits`: โมเดลอ่านเป็นอักขระอื่น แต่ decoder เลือก digit ที่เป็นไปได้
- `qty_column_by_position`: อ่านหัวตารางไม่พบ จึงใช้ตำแหน่งคอลัมน์สำรอง
- `blank_detection_uncertain`: หมึกน้อยหรือรบกวนเกินกว่าจะตัดสินได้ชัด

ค่า threshold และกฎอยู่ใน `configs/changhouse.yaml`; เหตุผลเชิงรายละเอียดอยู่ใกล้ logic ใน `postprocessing.py` และ `blank_detector.py`

## ปรับกฎอย่างไร

1. เก็บภาพพร้อม label ที่มนุษย์ยืนยันแล้ว
2. แก้ config หรือ logic เพียงประเด็นเดียว
3. เพิ่ม regression test สำหรับกรณีนั้น
4. รัน test ทั้งชุดและประเมินผลใหม่
5. บันทึกผลที่ยืนยันได้ใน pull request หรือ release note

อย่าลด threshold เพียงเพื่อลดจำนวน `needs_review`; เป้าหมายคือไม่ปล่อยค่าผิดผ่านโดยไม่ถูกตรวจ
