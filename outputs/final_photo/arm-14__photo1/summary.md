# OCR summary — arm-14__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2223 x 2344
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=5, ok=1

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 23 | 0.967 | ok | tight_crop |  |
| 2 | 39 | 0.943 | needs_review | tight_crop | tight_vs_segments_disagree(39 vs 32) |
| 3 | 11 | 0.000 | needs_review | digit_segments | tight_vs_segments_disagree(1 vs 11); letters_mapped_to_digits('||'->11); low_confidence(0.000<0.85) |
| 4 | 10 | 0.796 | needs_review | tight_crop | low_confidence(0.796<0.85) |
| 5 | 30 | 0.696 | needs_review | tight_crop | low_confidence(0.696<0.85) |
| 6 | 29 | 0.970 | needs_review | tight_crop | tight_vs_segments_disagree(29 vs 21) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 10.8
- alignment: 283.1
- qty_column: 17.5
- table_extraction: 0.1
- blank_detection: 4.5
- preprocessing: 2.7
- ocr_inference: 329.0
- total: 657.0
