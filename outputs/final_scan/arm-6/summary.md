# OCR summary — arm-6

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=3, ok=3

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 32 | 0.966 | ok | tight_crop |  |
| 2 | 64 | 0.998 | ok | tight_crop |  |
| 3 | 72 | 0.781 | needs_review | tight_crop | low_confidence(0.781<0.85) |
| 4 | 53 | 0.481 | needs_review | tight_crop | letters_mapped_to_digits('S3'->53); low_confidence(0.481<0.85) |
| 5 | 44 | 0.980 | ok | tight_crop |  |
| 6 | 65 | 0.275 | needs_review | tight_crop | letters_mapped_to_digits('bs'->65); low_confidence(0.275<0.85) |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 4.3
- alignment: 219.8
- qty_column: 15.9
- table_extraction: 0.1
- blank_detection: 3.1
- preprocessing: 1.8
- ocr_inference: 305.7
- total: 559.0
