# OCR summary — arm-12__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1928 x 2033
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=3, ok=3

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 88 | 0.963 | ok | tight_crop |  |
| 2 | 99 | 0.796 | needs_review | tight_crop | low_confidence(0.796<0.85) |
| 3 | 91 | 0.459 | needs_review | tight_crop | possible_merged_digits(9->91, penalty=0.015); low_confidence(0.459<0.85) |
| 4 | 95 | 0.985 | ok | tight_crop |  |
| 5 | 36 | 0.997 | ok | tight_crop |  |
| 6 | 66 | 0.237 | needs_review | tight_crop | letters_mapped_to_digits('品6'->66); low_confidence(0.237<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 15.9
- alignment: 379.6
- table_extraction: 0.1
- blank_detection: 3.4
- preprocessing: 1.9
- ocr_inference: 844.6
- total: 1256.2
