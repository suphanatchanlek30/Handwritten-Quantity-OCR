# OCR summary — arm-18__photo1

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1755 x 1850
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=5, needs_review=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 1 | 0.005 | needs_review | tight_crop | blank_detection_uncertain; letters_mapped_to_digits('ı'->1); low_confidence(0.005<0.85) |
| 2 | 1 | 0.173 | needs_review | tight_crop | low_confidence(0.173<0.85); ink_groups_exceed_digits(2>1) |
| 3 | 1 | 0.733 | needs_review | tight_crop | low_confidence(0.733<0.85) |
| 4 | 1 | 0.057 | needs_review | tight_crop | letters_mapped_to_digits('国'->1); low_confidence(0.057<0.85) |
| 5 | 1 | 0.394 | needs_review | tight_crop | low_confidence(0.394<0.85) |
| 6 | _blank_ |  | blank |  |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 6.2
- alignment: 281.5
- qty_column: 19.5
- table_extraction: 0.1
- blank_detection: 4.7
- preprocessing: 1.1
- ocr_inference: 143.2
- total: 462.5
