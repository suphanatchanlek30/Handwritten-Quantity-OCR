# OCR summary — example__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1768 x 2355
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 78 | 0.834 | needs_review | tight_crop | low_confidence(0.834<0.85) |
| 2 | 54 | 0.984 | ok | tight_crop |  |
| 3 | 79 | 0.722 | needs_review | tight_crop | low_confidence(0.722<0.85) |
| 4 | 36 | 0.976 | ok | tight_crop |  |
| 5 | 289 | 0.991 | ok | tight_crop |  |
| 6 | 65 | 0.878 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 8.4
- alignment: 267.5
- qty_column: 18.2
- table_extraction: 0.1
- blank_detection: 5.0
- preprocessing: 1.9
- ocr_inference: 212.0
- total: 523.4
