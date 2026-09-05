# El7amla League

موقع دوري الفانتازي الخاص بينا — 2v2 Fantasy League.

## هيكل المشروع

- `index.html`, `standings.html`, `teams.html`, `fixtures.html`, `khawas.html` — الصفحات
- `css/style.css` — التصميم المشترك لكل الصفحات
- `js/shared.js` — الدوال المشتركة (جلب البيانات، بناء الجداول، الحماية من XSS)
- `data/teams-config.json` — الفرق وألوانها (مصدر واحد بدل التكرار في كل صفحة)
- `data/league.json` — ربط كل لاعب برقمه في Fantasy Premier League
- `data/fixtures.json` — جدول المباريات
- `data/standings.json` — الترتيب الحالي (بيتحدث أوتوماتيك)
- `scripts/update_standings.py` — سكريبت بايثون بيسحب من FPL API ويحسب الترتيب
- `.github/workflows/` — الأتمتة (تشغيل السكريبت يومياً)

## طريقة التشغيل محلياً

افتح `index.html` بامتداد Live Server في VS Code، أو أي سيرفر ستاتيك بسيط.
