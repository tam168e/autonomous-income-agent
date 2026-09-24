# Provider Contract

هر منبع درآمد باید این مشخصات را اعلام کند:

- id
- name
- countryAvailability
- requiresKyc
- requiresCapital
- automationAllowed
- officialApiAvailable
- supportedCurrencies
- supportedNetworks
- minimumWithdrawalUsd
- withdrawalMethods
- estimatedHourlyUsd
- feeUsd
- riskLevel
- lastVerifiedAt

### State machine
`DISCOVERED -> VERIFIED -> ELIGIBLE -> SELECTED -> RUNNING -> EARNED -> WITHDRAWABLE -> PAID`

مسیرهای خطا:
`REJECTED`, `UNAVAILABLE_IN_COUNTRY`, `USER_ACTION_REQUIRED`, `FAILED`, `PAUSED`
