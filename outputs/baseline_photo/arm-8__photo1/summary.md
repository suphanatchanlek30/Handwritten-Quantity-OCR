# OCR summary — arm-8__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2830 x 2984
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 22 | 0.971 | ok | tight_crop |  |
| 2 | 39 | 0.831 | needs_review | tight_crop | tight_vs_segments_disagree(39 vs 32); low_confidence(0.831<0.85) |
| 3 | 68 | 0.713 | needs_review | tight_crop | tight_vs_segments_disagree(68 vs 63); low_confidence(0.713<0.85) |
| 4 | 74 | 0.998 | ok | tight_crop |  |
| 5 | 99 | 0.998 | ok | tight_crop |  |
| 6 | 14 | 0.959 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 34.9
- alignment: 321.6
- table_extraction: 0.1
- blank_detection: 3.9
- preprocessing: 2.1
- ocr_inference: 1014.8
- total: 1389.2
