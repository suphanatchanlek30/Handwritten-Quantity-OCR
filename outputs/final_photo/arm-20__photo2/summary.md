# OCR summary — arm-20__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2132 x 2248
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=4, ok=2

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 13 | 0.931 | ok | tight_crop |  |
| 2 | 14 | 0.833 | needs_review | tight_crop | low_confidence(0.833<0.85) |
| 3 | 12 | 0.590 | needs_review | tight_crop | low_confidence(0.590<0.85) |
| 4 | 3 | 0.779 | needs_review | tight_crop | low_confidence(0.779<0.85) |
| 5 | 0 | 0.210 | needs_review | tight_crop | low_confidence(0.210<0.85) |
| 6 | 9 | 0.992 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 8.1
- alignment: 249.6
- qty_column: 18.2
- table_extraction: 0.1
- blank_detection: 3.6
- preprocessing: 1.4
- ocr_inference: 258.7
- total: 548.4
