# OCR summary — arm-15__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2582 x 2723
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 42 | 0.909 | ok | tight_crop |  |
| 2 | 31 | 0.966 | ok | tight_crop |  |
| 3 | 13 | 0.889 | ok | tight_crop |  |
| 4 | 12 | 0.720 | needs_review | tight_crop | low_confidence(0.720<0.85) |
| 5 | 5 | 0.629 | needs_review | tight_crop | low_confidence(0.629<0.85) |
| 6 | 8 | 0.999 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 13.1
- alignment: 295.3
- qty_column: 17.2
- table_extraction: 0.1
- blank_detection: 3.3
- preprocessing: 1.5
- ocr_inference: 257.9
- total: 596.3
