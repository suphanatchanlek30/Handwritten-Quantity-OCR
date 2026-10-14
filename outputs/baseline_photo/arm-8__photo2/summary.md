# OCR summary — arm-8__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1420 x 1497
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=4, ok=2

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 22 | 0.988 | needs_review | tight_crop | tight_vs_segments_disagree(22 vs 72) |
| 2 | 32 | 0.985 | needs_review | tight_crop | tight_vs_segments_disagree(32 vs 37) |
| 3 | 68 | 0.532 | needs_review | tight_crop | low_confidence(0.532<0.85) |
| 4 | 74 | 0.995 | ok | tight_crop |  |
| 5 | 99 | 0.998 | ok | tight_crop |  |
| 6 | 14 | 0.546 | needs_review | tight_crop | letters_mapped_to_digits('[4'->14); low_confidence(0.546<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 9.2
- alignment: 248.7
- table_extraction: 0.1
- blank_detection: 3.2
- preprocessing: 2.4
- ocr_inference: 979.8
- total: 1255.0
