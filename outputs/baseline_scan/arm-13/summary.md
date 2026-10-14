# OCR summary — arm-13

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 12 | 0.942 | ok | tight_crop |  |
| 2 | 14 | 0.989 | ok | tight_crop |  |
| 3 | 32 | 0.925 | ok | tight_crop |  |
| 4 | 63 | 0.956 | ok | tight_crop |  |
| 5 | 72 | 0.789 | needs_review | tight_crop | low_confidence(0.789<0.85) |
| 6 | 81 | 0.988 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 12.5
- alignment: 249.0
- table_extraction: 0.1
- blank_detection: 2.8
- preprocessing: 2.0
- ocr_inference: 956.1
- total: 1233.6
