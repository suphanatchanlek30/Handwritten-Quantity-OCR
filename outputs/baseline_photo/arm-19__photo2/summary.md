# OCR summary — arm-19__photo2

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1571 x 1656
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=3, ok=3

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 14 | 0.712 | needs_review | tight_crop | letters_mapped_to_digits('|4'->14); low_confidence(0.712<0.85) |
| 2 | 12 | 0.243 | needs_review | tight_crop | possible_merged_digits(2->12, penalty=0.024); low_confidence(0.243<0.85) |
| 3 | 11 | 0.007 | needs_review | digit_segments | tight_vs_segments_disagree(1 vs 11); letters_mapped_to_digits('||'->11); low_confidence(0.007<0.85) |
| 4 | 23 | 0.984 | ok | tight_crop |  |
| 5 | 24 | 0.992 | ok | tight_crop |  |
| 6 | 44 | 0.999 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 11.2
- alignment: 247.1
- table_extraction: 0.1
- blank_detection: 3.5
- preprocessing: 2.3
- ocr_inference: 949.0
- total: 1223.5
