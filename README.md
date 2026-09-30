# Autonomous Income Agent

پروژه پایه برای یک Agent درآمدی اندرویدی با معماری ماژولار و قابل توسعه.

## Portfolio
برای معرفی خدمات Python/AI Automation و نمونه‌کارهای قابل ارائه به مشتری:
- [`PORTFOLIO.md`](PORTFOLIO.md)

## وضعیت مهم
این repository یک **پروژه اجرایی واقعی** است، اما عمداً هیچ درآمد، تراکنش یا Provider ساختگی تولید نمی‌کند. لایه‌های کشف فرصت، ارزیابی، تصمیم‌گیری، پس‌زمینه، کیف پول و برداشت آماده شده‌اند و برای فعال‌شدن درآمد واقعی باید Providerهای قانونی و دارای API/Automation مجاز به آن اضافه شوند.

### اجزای پروژه
- `android/` اپلیکیشن Android با Kotlin + Jetpack Compose
- `backend/` Backend اختیاری FastAPI برای فهرست فرصت‌ها و اتصال امن به Providerها
- `docs/` مستندات معماری و قرارداد Providerها

### ساخت Android
1. پوشه `android` را در Android Studio باز کنید.
2. با Android SDK 35 و JDK 17+ پروژه را Sync کنید.
3. سپس `Build > Build APK(s)` را اجرا کنید.

> اگر Android Studio هنگام Sync نسخه جدیدتر AGP/Kotlin پیشنهاد کرد، اجازه بدهید IDE نسخه سازگار را اعمال کند؛ APIها طوری نوشته شده‌اند که وابستگی به نسخه خاص حداقلی باشد.

### اجرای Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

برای Emulator اندروید، URL پیش‌فرض Backend در `BuildConfig` برابر `http://10.0.2.2:8000` است. برای production از HTTPS استفاده کنید.

## چیزی که این پروژه عمداً انجام نمی‌دهد
- جعل کشور/هویت/KYC
- دور زدن محدودیت جغرافیایی یا تحریم
- CAPTCHA/anti-bot bypass
- کلیک یا مشاهده جعلی تبلیغات
- نگهداری Seed Phrase/Private Key روی سرور
- نمایش درآمد ساختگی
- اجرای تراکنش واقعی بدون Provider/Wallet implementation و کنترل‌های امنیتی لازم
