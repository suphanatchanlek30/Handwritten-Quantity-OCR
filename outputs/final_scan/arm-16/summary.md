# OCR summary — arm-16

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=2, ok=4

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 22 | 0.996 | ok | tight_crop |  |
| 2 | 38 | 0.817 | needs_review | tight_crop | tight_vs_segments_disagree(38 vs 39); low_confidence(0.817<0.85) |
| 3 | 64 | 0.984 | ok | tight_crop |  |
| 4 | 47 | 0.995 | ok | tight_crop |  |
| 5 | 49 | 0.989 | ok | tight_crop |  |
| 6 | 55 | 0.612 | needs_review | tight_crop | letters_mapped_to_digits('S5'->55); low_confidence(0.612<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 5.2
- alignment: 218.8
- qty_column: 16.5
- table_extraction: 0.1
- blank_detection: 2.7
- preprocessing: 1.9
- ocr_inference: 327.2
- total: 580.0
