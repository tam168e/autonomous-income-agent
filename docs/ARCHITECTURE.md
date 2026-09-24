# Architecture

```text
Android UI
   |
   +--> Income Repository
   |        |
   |        +--> Provider Registry
   |        +--> Opportunity Discovery Engine
   |        +--> Evaluation/Scoring Engine
   |        +--> Decision Engine
   |        +--> Execution Engine
   |
   +--> Wallet Manager
   +--> Withdrawal Coordinator
   +--> SQLite local storage
   +--> WorkManager background scheduling
   |
   +--> Optional Secure Backend
             |
             +--> Provider adapters
             +--> opportunity feeds
```

## اصول
- Providerها مستقل و قابل افزوده‌شدن هستند.
- هر Provider ابتدا Eligibility و Automation policy را مشخص می‌کند.
- درآمد فقط وقتی ثبت می‌شود که Payment ID یا مدرک قابل‌اعتبارسنجی وجود داشته باشد.
- Wallet مقصد شامل `address + network + asset` است.
- هیچ Secret در APK یا لاگ ذخیره نمی‌شود.
