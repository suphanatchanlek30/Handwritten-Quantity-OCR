# OCR summary — arm-7

- Template: `CHANGHOUSE_AUTO`
- Model: `PP-OCRv5_server_rec`
- Document status: **completed**
- Image: 1667 x 1759
- Alignment: auto_rectify (success=True, fallback=False)
- Field status counts: blank=4, needs_review=1, ok=5

> `confidence` คือ `rec_score` ของโมเดล ไม่ใช่ความแม่นยำที่วัดจริง

| row | qty | confidence | status | variant | review reasons |
|---:|---|---:|---|---|---|
| 1 | 32 | 0.990 | ok | tight_crop |  |
| 2 | 22 | 0.987 | ok | tight_crop |  |
| 3 | 68 | 0.993 | ok | tight_crop |  |
| 4 | 12 | 0.835 | needs_review | tight_crop | low_confidence(0.835<0.85) |
| 5 | 23 | 0.994 | ok | tight_crop |  |
| 6 | 27 | 0.995 | ok | tight_crop |  |
| 7 | _blank_ |  | blank |  |  |
| 8 | _blank_ |  | blank |  |  |
| 9 | _blank_ |  | blank |  |  |
| 10 | _blank_ |  | blank |  |  |

## Timings (ms)

- load: 11.5
- alignment: 247.8
- table_extraction: 0.1
- blank_detection: 2.9
- preprocessing: 1.7
- ocr_inference: 853.2
- total: 1128.5
