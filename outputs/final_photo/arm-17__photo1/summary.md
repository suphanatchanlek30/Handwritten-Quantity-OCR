# OCR summary — arm-17__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2154 x 2271
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 3 | 0.851 | ok | tight_crop |  |
| 2 | 14 | 0.967 | ok | tight_crop |  |
| 3 | 18 | 0.993 | ok | tight_crop |  |
| 4 | 22 | 0.957 | ok | tight_crop |  |
| 5 | 64 | 0.982 | ok | tight_crop |  |
| 6 | 38 | 0.731 | needs_review | tight_crop | low_confidence(0.731<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 9.2
- alignment: 271.7
- qty_column: 18.4
- table_extraction: 0.1
- blank_detection: 4.5
- preprocessing: 2.3
- ocr_inference: 292.6
- total: 608.0
