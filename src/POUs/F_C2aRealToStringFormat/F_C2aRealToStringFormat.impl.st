IF eDecimalSeparator = E_C2aDecimalSeparator.COMMA THEN
    sSep := ',';
ELSE
    sSep := '.';
END_IF
IF ABS(rValueToConvert) > GVL_C2aConst.EXP_THRESHOLD THEN
    F_C2aRealToStringFormat := REAL_TO_STRING(rValueToConvert);
    IF sSep = ',' AND FIND(F_C2aRealToStringFormat, '.') > 0 THEN
        F_C2aRealToStringFormat := REPLACE(F_C2aRealToStringFormat, ',', 1, FIND(F_C2aRealToStringFormat, '.'));
    END_IF
    RETURN;
END_IF
usiDigits := MIN(usiSignificantDigitsCount, GVL_C2aConst.MAX_FRACTION_DIGITS);
uliPow := 1;
FOR usiIdx := 1 TO usiDigits DO
    uliPow := uliPow * 10;  // lint:allow STL008 десятичная система
END_FOR
lrAbs := ABS(REAL_TO_LREAL(rValueToConvert));
lrScaled := lrAbs * ULINT_TO_LREAL(uliPow) + 0.5;  // lint:allow STL008 округление половины вверх
// LREAL_TO_ULINT округляет к ближайшему — приводим к floor(x + 0.5)
uliScaled := LREAL_TO_ULINT(lrScaled);
IF ULINT_TO_LREAL(uliScaled) > lrScaled THEN
    uliScaled := uliScaled - 1;
END_IF
uliInt := uliScaled / uliPow;
uliFrac := uliScaled MOD uliPow;
F_C2aRealToStringFormat := ULINT_TO_STRING(uliInt);
IF usiDigits > 0 THEN
    sFrac := ULINT_TO_STRING(uliFrac);
    WHILE LEN(sFrac) < USINT_TO_INT(usiDigits) DO
        sFrac := CONCAT('0', sFrac);
    END_WHILE
    F_C2aRealToStringFormat := CONCAT(CONCAT(F_C2aRealToStringFormat, sSep), sFrac);
END_IF
IF rValueToConvert < 0.0 AND uliScaled > 0 THEN
    F_C2aRealToStringFormat := CONCAT('-', F_C2aRealToStringFormat);
END_IF
