# OCR summary — arm-6__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2601 x 2743
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=4, ok=2

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 32 | 0.980 | ok | tight_crop |  |
| 2 | 14 | 0.704 | needs_review | tight_crop | low_confidence(0.704<0.85) |
| 3 | 72 | 0.732 | needs_review | tight_crop | low_confidence(0.732<0.85) |
| 4 | 55 | 0.305 | needs_review | tight_crop | tight_vs_segments_disagree(55 vs 53); letters_mapped_to_digits('S5'->55); low_confidence(0.305<0.85) |
| 5 | 44 | 0.991 | ok | tight_crop |  |
| 6 | 65 | 0.050 | needs_review | tight_crop | letters_mapped_to_digits('bs'->65); low_confidence(0.050<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 13.2
- alignment: 295.0
- qty_column: 17.7
- table_extraction: 0.1
- blank_detection: 3.3
- preprocessing: 1.8
- ocr_inference: 332.7
- total: 672.7
