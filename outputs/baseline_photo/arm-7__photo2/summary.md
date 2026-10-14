# OCR summary — arm-7__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1405 x 1481
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=4, ok=2

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 82 | 0.721 | needs_review | tight_crop | tight_vs_segments_disagree(82 vs 32); low_confidence(0.721<0.85) |
| 2 | 22 | 0.711 | needs_review | tight_crop | low_confidence(0.711<0.85) |
| 3 | 18 | 0.322 | needs_review | tight_crop | possible_merged_digits(1->18, penalty=0.035); tight_vs_segments_disagree(18 vs 68); low_confidence(0.322<0.85) |
| 4 | 12 | 0.171 | needs_review | tight_crop | possible_merged_digits(1->12, penalty=-0.001); low_confidence(0.171<0.85) |
| 5 | 23 | 0.967 | ok | tight_crop |  |
| 6 | 27 | 0.980 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 7.9
- alignment: 252.7
- table_extraction: 0.1
- blank_detection: 3.3
- preprocessing: 2.3
- ocr_inference: 965.0
- total: 1241.7
