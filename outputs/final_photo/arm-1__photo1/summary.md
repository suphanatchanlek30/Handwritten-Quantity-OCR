# OCR summary — arm-1__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2506 x 2643
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 15 | 0.988 | ok | tight_crop |  |
| 2 | 23 | 0.964 | ok | tight_crop |  |
| 3 | 29 | 0.912 | ok | tight_crop |  |
| 4 | 32 | 0.992 | ok | tight_crop |  |
| 5 | 49 | 0.691 | needs_review | tight_crop | low_confidence(0.691<0.85) |
| 6 | 48 | 0.997 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 18.1
- alignment: 259.2
- qty_column: 20.9
- table_extraction: 0.1
- blank_detection: 4.1
- preprocessing: 1.0
- ocr_inference: 145.0
- total: 455.1
