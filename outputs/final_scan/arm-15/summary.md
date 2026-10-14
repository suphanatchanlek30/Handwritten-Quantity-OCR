# OCR summary — arm-15

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 42 | 0.796 | needs_review | tight_crop | tight_vs_segments_disagree(42 vs 49); low_confidence(0.796<0.85) |
| 2 | 31 | 0.970 | ok | tight_crop |  |
| 3 | 13 | 0.884 | ok | tight_crop |  |
| 4 | 12 | 0.955 | ok | tight_crop |  |
| 5 | 9 | 0.351 | needs_review | tight_crop | low_confidence(0.351<0.85) |
| 6 | 8 | 0.992 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 3.6
- alignment: 217.3
- qty_column: 16.6
- table_extraction: 0.1
- blank_detection: 2.7
- preprocessing: 1.5
- ocr_inference: 259.2
- total: 508.1
