# اختبارات المتصفح

تشغّل التطبيق في Chromium بميكروفون وهمي وتمرّ بمسارات الأطفال الثلاثة وولي الأمر والمسرح والكتاب والنسخ الاحتياطية.

```bash
pip install playwright && playwright install chromium
python3 tests/e2e_run.py && python3 tests/e2e_run2.py && python3 tests/e2e_run3.py
```
كل سطر ✓ خطوة نجحت؛ آخر السجل يطبع الأخطاء أو none.
