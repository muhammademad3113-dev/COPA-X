# COPA X — Universal Android

هذا المشروع مهيأ للبناء من GitHub Actions من الهاتف.

## الملفات
- `main.py`: واجهة التطبيق ومحرك yt-dlp.
- `pyproject.toml`: إعداد Flet وUniversal APK.
- `requirements.txt`: الاعتمادات.
- `.github/workflows/build-apk.yml`: يبني FFmpeg وQuickJS لكل ABI ثم يبني APK واحد Universal.

## ماذا يفعل الـWorkflow؟
1. يثبت Python وFlet وyt-dlp/EJS.
2. يثبت Android NDK.
3. ينزل FFmpeg Android الجاهز لأربع معماريات.
4. يبني QuickJS-NG من المصدر لأربع معماريات.
5. يضع FFmpeg وQuickJS داخل `assets/bin/<abi>/`.
6. يبني APK Universal واحد.
7. يرفعه كـArtifact باسم `COPA-X-Universal`.

## مهم
Universal في Flet يعني APK واحدًا يحتوي المعماريات المدعومة: arm64-v8a وarmeabi-v7a وx86_64 وx86. Flet الحالي يدعم هذه المعماريات؛ x86 غير مدعوم في Flet 0.86+ وفق وثائق Flet، لذلك إذا رفض إصدار Flet الأحدث x86 فسيكون البناء متوافقًا مع المعماريات التي يدعمها ذلك الإصدار.

خطأ 403 لا يمكن ضمان إزالته لأن المنصة قد تتطلب تسجيل دخول/كوكيز أو ترفض الطلب. JavaScript/EJS وFFmpeg هنا مجهزان فعليًا داخل عملية البناء.
