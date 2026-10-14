# OCR summary — arm-17

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, ok=6

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 3 | 0.901 | ok | tight_crop |  |
| 2 | 14 | 0.997 | ok | tight_crop |  |
| 3 | 18 | 0.997 | ok | tight_crop |  |
| 4 | 22 | 0.974 | ok | tight_crop |  |
| 5 | 64 | 0.991 | ok | tight_crop |  |
| 6 | 38 | 0.934 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 12.5
- alignment: 248.1
- table_extraction: 0.1
- blank_detection: 2.7
- preprocessing: 1.7
- ocr_inference: 850.6
- total: 1126.5
