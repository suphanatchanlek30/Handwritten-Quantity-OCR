# OCR summary — arm-18

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 12 | 0.910 | ok | tight_crop |  |
| 2 | 18 | 0.998 | ok | tight_crop |  |
| 3 | 32 | 0.985 | ok | tight_crop |  |
| 4 | 64 | 0.992 | ok | tight_crop |  |
| 5 | 42 | 0.968 | ok | tight_crop |  |
| 6 | 11 | 0.022 | needs_review | tight_crop | possible_merged_digits(1->11, penalty=0.003); letters_mapped_to_digits("'"->1); low_confidence(0.022<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 12.5
- alignment: 247.8
- table_extraction: 0.1
- blank_detection: 2.8
- preprocessing: 1.7
- ocr_inference: 873.6
- total: 1149.1
