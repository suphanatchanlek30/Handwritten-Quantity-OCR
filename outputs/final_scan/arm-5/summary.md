# OCR summary — arm-5

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=3, ok=3

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 23 | 0.817 | needs_review | tight_crop | tight_vs_segments_disagree(23 vs 93); low_confidence(0.817<0.85) |
| 2 | 31 | 1.000 | ok | tight_crop |  |
| 3 | 42 | 0.824 | needs_review | tight_crop | low_confidence(0.824<0.85) |
| 4 | 68 | 0.998 | ok | tight_crop |  |
| 5 | 76 | 0.955 | ok | tight_crop |  |
| 6 | 59 | 0.008 | needs_review | tight_crop | possible_merged_digits(5->59, penalty=0.020); tight_vs_segments_disagree(59 vs 53); letters_mapped_to_digits('S'->5); low_confidence(0.008<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 5.3
- alignment: 215.9
- qty_column: 15.7
- table_extraction: 0.1
- blank_detection: 3.2
- preprocessing: 1.9
- ocr_inference: 291.9
- total: 541.3
