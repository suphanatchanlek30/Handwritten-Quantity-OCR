# OCR summary — arm-17__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2726 x 2875
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 3 | 0.800 | needs_review | tight_crop | low_confidence(0.800<0.85) |
| 2 | 14 | 0.918 | ok | tight_crop |  |
| 3 | 18 | 0.992 | ok | tight_crop |  |
| 4 | 22 | 0.992 | ok | tight_crop |  |
| 5 | 64 | 0.956 | ok | tight_crop |  |
| 6 | 38 | 0.715 | needs_review | tight_crop | low_confidence(0.715<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 15.5
- alignment: 324.8
- qty_column: 16.5
- table_extraction: 0.1
- blank_detection: 3.4
- preprocessing: 1.5
- ocr_inference: 260.2
- total: 630.3
