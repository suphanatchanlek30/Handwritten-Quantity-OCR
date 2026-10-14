# OCR summary — arm-12

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, ok=6

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 88 | 0.998 | ok | tight_crop |  |
| 2 | 89 | 0.885 | ok | tight_crop |  |
| 3 | 96 | 0.977 | ok | tight_crop |  |
| 4 | 95 | 0.997 | ok | tight_crop |  |
| 5 | 36 | 0.992 | ok | tight_crop |  |
| 6 | 66 | 0.986 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 4.4
- alignment: 216.7
- qty_column: 15.8
- table_extraction: 0.1
- blank_detection: 3.6
- preprocessing: 3.1
- ocr_inference: 306.2
- total: 557.5
