# OCR summary — arm-16__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1577 x 1663
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 22 | 0.988 | ok | tight_crop |  |
| 2 | 38 | 0.913 | needs_review | tight_crop | tight_vs_segments_disagree(38 vs 32) |
| 3 | 64 | 0.976 | ok | tight_crop |  |
| 4 | 47 | 0.998 | ok | tight_crop |  |
| 5 | 49 | 0.997 | ok | tight_crop |  |
| 6 | 55 | 0.831 | needs_review | tight_crop | low_confidence(0.831<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 5.8
- alignment: 230.4
- qty_column: 18.2
- table_extraction: 0.1
- blank_detection: 4.3
- preprocessing: 2.9
- ocr_inference: 380.4
- total: 651.8
