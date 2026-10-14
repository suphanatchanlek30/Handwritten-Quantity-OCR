# OCR summary — arm-19__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 3086 x 3254
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 14 | 0.815 | needs_review | tight_crop | low_confidence(0.815<0.85) |
| 2 | 12 | 0.915 | ok | tight_crop |  |
| 3 | 11 | 0.009 | needs_review | digit_segments | tight_vs_segments_disagree(1 vs 11); letters_mapped_to_digits('||'->11); low_confidence(0.009<0.85) |
| 4 | 23 | 0.986 | ok | tight_crop |  |
| 5 | 24 | 0.992 | ok | tight_crop |  |
| 6 | 44 | 0.999 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 38.3
- alignment: 359.2
- table_extraction: 0.1
- blank_detection: 3.8
- preprocessing: 2.3
- ocr_inference: 952.3
- total: 1366.7
