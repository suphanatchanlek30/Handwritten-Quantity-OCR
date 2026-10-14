# OCR summary — arm-9__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2991 x 3154
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 7 | 0.999 | ok | tight_crop |  |
| 2 | 8 | 0.998 | ok | tight_crop |  |
| 3 | 3 | 0.634 | needs_review | tight_crop | low_confidence(0.634<0.85) |
| 4 | 2 | 0.994 | ok | tight_crop |  |
| 5 | 18 | 0.987 | ok | tight_crop |  |
| 6 | 14 | 0.975 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 37.4
- alignment: 343.6
- table_extraction: 0.1
- blank_detection: 4.2
- preprocessing: 1.3
- ocr_inference: 527.7
- total: 923.5
