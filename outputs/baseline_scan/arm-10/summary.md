# OCR summary — arm-10

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 12 | 0.992 | ok | tight_crop |  |
| 2 | 13 | 0.805 | needs_review | tight_crop | low_confidence(0.805<0.85) |
| 3 | 86 | 0.978 | ok | tight_crop |  |
| 4 | 97 | 0.993 | ok | tight_crop |  |
| 5 | 63 | 0.726 | needs_review | tight_crop | low_confidence(0.726<0.85) |
| 6 | 72 | 0.954 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 11.4
- alignment: 245.0
- table_extraction: 0.1
- blank_detection: 2.8
- preprocessing: 1.9
- ocr_inference: 954.7
- total: 1227.2
