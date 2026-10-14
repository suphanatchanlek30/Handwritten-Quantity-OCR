# OCR summary — arm-3__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1730 x 1824
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, ok=6

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 98 | 0.909 | ok | tight_crop |  |
| 2 | 97 | 0.998 | ok | tight_crop |  |
| 3 | 63 | 0.992 | ok | tight_crop |  |
| 4 | 12 | 0.995 | ok | tight_crop |  |
| 5 | 14 | 0.985 | ok | tight_crop |  |
| 6 | 22 | 0.870 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 6.8
- alignment: 218.3
- qty_column: 16.4
- table_extraction: 0.1
- blank_detection: 3.3
- preprocessing: 1.3
- ocr_inference: 230.4
- total: 485.5
