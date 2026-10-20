sResult := sInputString;
iGuard := 0;
WHILE LEN(sResult) < USINT_TO_INT(usiTargetLen) AND LEN(sAddChar) > 0
        AND iGuard < 255 DO  // lint:allow STL008 STRING(255)
    IF xRight THEN
        sResult := CONCAT(sResult, sAddChar);
    ELSE
        sResult := CONCAT(sAddChar, sResult);
    END_IF
    iGuard := iGuard + 1;
END_WHILE
F_C2aAddChar := sResult;
