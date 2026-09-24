# Prompt for Google AI Studio

You are given an existing Android/Backend codebase named Autonomous Income Agent.
Do NOT restart from a blank project and do NOT stop at architecture prose.
Open the existing files, inspect the code, compile it, fix all errors, and continue implementation in the repository.

Goal: turn this codebase into a production-oriented autonomous income agent that only executes real, legal, zero-capital opportunities with permitted automation and verifiable payouts.

Hard requirements:
1. Do not invent providers or earnings.
2. Do not ask again for the user's country; country is Iran and must be handled by CountryEligibilityEngine.
3. Never spoof country, identity, KYC, address, tax data, SIM, device identity, or residency.
4. Never bypass CAPTCHA, anti-bot, rate limits, or provider restrictions.
5. Use official APIs or explicit automation permissions only.
6. Keep Provider adapters modular. One unavailable provider must not stop the app.
7. Add real providers only after verifying their current terms, geography, payment method, minimum payout, and automation policy.
8. Keep wallet destination as address + network + asset. Validate all three before a transfer.
9. Never place API secrets or wallet seed/private keys in the APK.
10. Do not present fake/demo earnings as real earnings.
11. The Android app must continue permitted background work using WorkManager/Foreground Service where required by Android policy.
12. Build the APK and report the exact build output path. Do not declare complete until the project compiles.

If a provider requires KYC or a human action, mark it USER_ACTION_REQUIRED and continue scanning other providers.

When adding a provider, implement:
- provider metadata
- eligibility check
- discovery
- evaluation
- execution
- earnings verification
- withdrawal integration
- tests

At the end:
- compile Android project
- fix all compile/test issues
- provide APK path
- provide a short list of which modules are production-ready and which still require provider credentials or legal account setup
