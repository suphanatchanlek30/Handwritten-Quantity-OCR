# OCR summary — arm-14

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=4, ok=2

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 23 | 0.965 | ok | tight_crop |  |
| 2 | 39 | 0.773 | needs_review | tight_crop | low_confidence(0.773<0.85) |
| 3 | 11 | 0.050 | needs_review | tight_crop | possible_merged_digits(1->11, penalty=-0.002); letters_mapped_to_digits('|'->1); low_confidence(0.050<0.85) |
| 4 | 10 | 0.836 | needs_review | tight_crop | low_confidence(0.836<0.85) |
| 5 | 30 | 0.710 | needs_review | tight_crop | low_confidence(0.710<0.85) |
| 6 | 29 | 0.993 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 12.5
- alignment: 248.4
- table_extraction: 0.1
- blank_detection: 3.2
- preprocessing: 1.5
- ocr_inference: 648.5
- total: 928.2
