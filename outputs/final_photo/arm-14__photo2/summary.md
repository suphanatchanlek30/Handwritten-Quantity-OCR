# OCR summary — arm-14__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 2420 x 2552
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 23 | 0.938 | ok | tight_crop |  |
| 2 | 39 | 0.906 | needs_review | tight_crop | tight_vs_segments_disagree(39 vs 32) |
| 3 | 11 | 0.001 | needs_review | digit_segments | tight_vs_segments_disagree(1 vs 11); letters_mapped_to_digits('||'->11); low_confidence(0.001<0.85) |
| 4 | 10 | 0.880 | ok | tight_crop |  |
| 5 | 30 | 0.898 | ok | tight_crop |  |
| 6 | 29 | 0.996 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 10.3
- alignment: 283.2
- qty_column: 16.5
- table_extraction: 0.1
- blank_detection: 3.5
- preprocessing: 1.5
- ocr_inference: 235.0
- total: 558.7
