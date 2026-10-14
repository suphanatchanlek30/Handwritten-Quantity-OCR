# OCR summary — arm-9

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, ok=6

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 7 | 0.999 | ok | tight_crop |  |
| 2 | 8 | 0.999 | ok | tight_crop |  |
| 3 | 3 | 0.993 | ok | tight_crop |  |
| 4 | 2 | 0.984 | ok | tight_crop |  |
| 5 | 18 | 0.927 | ok | tight_crop |  |
| 6 | 14 | 0.978 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 5.4
- alignment: 220.6
- qty_column: 15.7
- table_extraction: 0.1
- blank_detection: 2.6
- preprocessing: 1.0
- ocr_inference: 162.9
- total: 414.2
