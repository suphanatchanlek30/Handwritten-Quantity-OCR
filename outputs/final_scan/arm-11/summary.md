# OCR summary — arm-11

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, ok=6

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 13 | 0.964 | ok | tight_crop |  |
| 2 | 14 | 0.950 | ok | tight_crop |  |
| 3 | 36 | 0.988 | ok | tight_crop |  |
| 4 | 42 | 0.883 | ok | tight_crop |  |
| 5 | 53 | 0.989 | ok | tight_crop |  |
| 6 | 84 | 0.998 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 5.4
- alignment: 221.9
- qty_column: 15.9
- table_extraction: 0.1
- blank_detection: 3.0
- preprocessing: 2.3
- ocr_inference: 326.7
- total: 582.9
