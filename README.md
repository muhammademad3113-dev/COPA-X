
# COPA X — Universal Android APK

هذا المشروع مخصص للبناء من الهاتف عن طريق GitHub Actions.

## ماذا تم إصلاحه؟
- yt-dlp حديث + yt-dlp-ejs.
- QuickJS-NG يُبنى داخل GitHub Actions لكل ABI.
- FFmpeg Android static يُجهز تلقائيًا.
- Universal APK يدعم:
  - arm64-v8a
  - armeabi-v7a
  - x86_64
- أسماء الملفات قصيرة مع Video ID.
- أفضل جودة باستخدام فيديو + صوت ثم دمج MP4.
- ترجمة SRT وترجمة آلية عند توفرها.
- Playlist ومجلد لكل فيديو.

## لماذا QuickJS؟
yt-dlp الحالي يستخدم EJS لحل تحديات JavaScript في YouTube، ويحتاج JavaScript runtime. الوثائق الرسمية تذكر Deno كخيار موصى به وQuickJS كخيار مدعوم. هذا المشروع يستخدم QuickJS-NG لتقليل الاعتماد على runtime خارجي في Android.

## البناء من الهاتف
1. أنشئ Repository جديدًا على GitHub.
2. ارفع الملفات.
3. افتح Actions.
4. اختر Build COPA X Universal APK.
5. اضغط Run workflow.
6. انتظر انتهاء البناء.
7. افتح Artifacts ثم `copa-x-universal-apk`.

## ملاحظة عن حجم APK
لأن Universal APK يحتوي ملفات native لأكثر من ABI، سيكون أكبر من APK مخصص لهاتف واحد. هذا مقصود لزيادة التوافق.

## 403
لا يمكن ضمان إزالة HTTP 403 بالكامل. 403 قد يكون رفضًا من المنصة أو بسبب جلسة/صلاحيات أو تغيّر في الحماية. المشروع يعالج جانب JavaScript/EJS والتنسيقات وإعادة المحاولة، لكنه لا يتجاوز CAPTCHA أو صلاحيات الحساب.

## الترخيص
راجع تراخيص Flet وyt-dlp وyt-dlp-ejs وQuickJS-NG وFFmpeg ومصدر FFmpeg Android المستخدم قبل التوزيع التجاري.
