# OCR summary — arm-20

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 13 | 0.980 | ok | tight_crop |  |
| 2 | 14 | 0.765 | needs_review | tight_crop | low_confidence(0.765<0.85) |
| 3 | 12 | 0.925 | ok | tight_crop |  |
| 4 | 3 | 0.940 | ok | tight_crop |  |
| 5 | 6 | 0.977 | ok | tight_crop |  |
| 6 | 9 | 0.997 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 12.3
- alignment: 249.3
- table_extraction: 0.1
- blank_detection: 2.8
- preprocessing: 1.3
- ocr_inference: 638.1
- total: 913.5
