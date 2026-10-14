# OCR summary — arm-6__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1418 x 1495
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=4, ok=2

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 32 | 0.979 | ok | tight_crop |  |
| 2 | 14 | 0.380 | needs_review | tight_crop | possible_merged_digits(1->14, penalty=-0.005); tight_vs_segments_disagree(14 vs 64); low_confidence(0.380<0.85) |
| 3 | 79 | 0.502 | needs_review | tight_crop | low_confidence(0.502<0.85) |
| 4 | 53 | 0.457 | needs_review | tight_crop | low_confidence(0.457<0.85) |
| 5 | 44 | 0.992 | ok | tight_crop |  |
| 6 | 65 | 0.276 | needs_review | tight_crop | letters_mapped_to_digits('bs'->65); low_confidence(0.276<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 4.9
- alignment: 243.3
- qty_column: 17.2
- table_extraction: 0.1
- blank_detection: 3.0
- preprocessing: 1.7
- ocr_inference: 259.2
- total: 537.7
