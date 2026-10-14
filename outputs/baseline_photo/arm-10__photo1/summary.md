# OCR summary — arm-10__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2775 x 2926
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 12 | 0.983 | ok | tight_crop |  |
| 2 | 13 | 0.726 | needs_review | tight_crop | low_confidence(0.726<0.85) |
| 3 | 86 | 0.971 | ok | tight_crop |  |
| 4 | 97 | 0.998 | ok | tight_crop |  |
| 5 | 69 | 0.871 | ok | tight_crop |  |
| 6 | 72 | 0.807 | needs_review | tight_crop | low_confidence(0.807<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 34.1
- alignment: 328.1
- table_extraction: 0.1
- blank_detection: 3.5
- preprocessing: 1.8
- ocr_inference: 848.5
- total: 1227.4
