diDays := UDINT_TO_DINT(udiUnix / GVL_C2aConst.SECONDS_PER_DAY);
udiSec := udiUnix MOD GVL_C2aConst.SECONDS_PER_DAY;
diZ := diDays + 719468;
diEra := diZ / 146097;
diDoe := diZ - diEra * 146097;
diYoe := (diDoe - diDoe / 1460 + diDoe / 36524 - diDoe / 146096) / 365;
diYear := diYoe + diEra * 400;
diDoy := diDoe - (365 * diYoe + diYoe / 4 - diYoe / 100);
diMp := (5 * diDoy + 2) / 153;
F_C2aUnixToDate.usiDay := DINT_TO_USINT(diDoy - (153 * diMp + 2) / 5 + 1);
IF diMp < 10 THEN
    diMonth := diMp + 3;
ELSE
    diMonth := diMp - 9;
END_IF
IF diMonth <= 2 THEN
    diYear := diYear + 1;
END_IF
F_C2aUnixToDate.uiYear := DINT_TO_UINT(diYear);
F_C2aUnixToDate.usiMonth := DINT_TO_USINT(diMonth);
F_C2aUnixToDate.usiHour := UDINT_TO_USINT(udiSec / 3600);
F_C2aUnixToDate.usiMinute := UDINT_TO_USINT((udiSec MOD 3600) / 60);
F_C2aUnixToDate.usiSecond := UDINT_TO_USINT(udiSec MOD 60);
// 1970-01-01 — четверг (4): ISO 1..7
F_C2aUnixToDate.usiDayOfWeek := DINT_TO_USINT((diDays + 3) MOD 7 + 1);
