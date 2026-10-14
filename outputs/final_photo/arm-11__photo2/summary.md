# OCR summary — arm-11__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2132 x 2248
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 13 | 0.973 | ok | tight_crop |  |
| 2 | 14 | 0.982 | ok | tight_crop |  |
| 3 | 36 | 0.968 | ok | tight_crop |  |
| 4 | 42 | 0.824 | needs_review | tight_crop | low_confidence(0.824<0.85) |
| 5 | 53 | 0.997 | ok | tight_crop |  |
| 6 | 84 | 0.999 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 7.3
- alignment: 243.2
- qty_column: 16.8
- table_extraction: 0.1
- blank_detection: 3.2
- preprocessing: 2.1
- ocr_inference: 337.8
- total: 620.0
