# OCR summary — arm-4

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, ok=6

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 77 | 0.999 | ok | tight_crop |  |
| 2 | 83 | 0.999 | ok | tight_crop |  |
| 3 | 21 | 0.997 | ok | tight_crop |  |
| 4 | 32 | 0.940 | ok | tight_crop |  |
| 5 | 64 | 0.984 | ok | tight_crop |  |
| 6 | 103 | 0.998 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 4.4
- alignment: 215.5
- qty_column: 16.4
- table_extraction: 0.1
- blank_detection: 2.7
- preprocessing: 1.7
- ocr_inference: 267.5
- total: 516.4
