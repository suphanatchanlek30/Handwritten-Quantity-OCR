# OCR summary — arm-8

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 22 | 0.988 | ok | tight_crop |  |
| 2 | 32 | 0.974 | ok | tight_crop |  |
| 3 | 63 | 0.719 | needs_review | tight_crop | low_confidence(0.719<0.85) |
| 4 | 74 | 0.992 | ok | tight_crop |  |
| 5 | 99 | 0.997 | ok | tight_crop |  |
| 6 | 14 | 0.982 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 4.3
- alignment: 219.8
- qty_column: 15.6
- table_extraction: 0.1
- blank_detection: 2.6
- preprocessing: 2.0
- ocr_inference: 329.5
- total: 582.2
