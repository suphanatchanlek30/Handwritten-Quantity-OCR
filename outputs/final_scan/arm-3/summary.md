# OCR summary — arm-3

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 98 | 0.632 | needs_review | tight_crop | letters_mapped_to_digits('G8'->98); low_confidence(0.632<0.85) |
| 2 | 97 | 0.996 | ok | tight_crop |  |
| 3 | 63 | 0.992 | ok | tight_crop |  |
| 4 | 12 | 0.996 | ok | tight_crop |  |
| 5 | 14 | 0.990 | ok | tight_crop |  |
| 6 | 22 | 0.928 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 5.2
- alignment: 202.4
- qty_column: 16.0
- table_extraction: 0.1
- blank_detection: 3.0
- preprocessing: 1.8
- ocr_inference: 282.8
- total: 518.3
