sValue := sInputString;
IF LEN(sPrefix) > 0 AND LEFT(sInputString, LEN(sPrefix)) = sPrefix THEN
    sValue := RIGHT(sInputString, LEN(sInputString) - LEN(sPrefix));
END_IF
wResult := 0;
FOR iChar := 0 TO LEN(sValue) - 1 DO
    bChar := sValue[iChar];
    iDigit := -1;
    IF bChar >= 16#30 AND bChar <= 16#39 THEN          // '0'..'9'
        iDigit := BYTE_TO_INT(bChar) - 16#30;
    ELSIF bChar >= 16#41 AND bChar <= 16#46 THEN       // 'A'..'F'
        iDigit := BYTE_TO_INT(bChar) - 16#41 + 10;  // lint:allow STL008 'A' = 10 в шестнадцатеричной записи
    ELSIF bChar >= 16#61 AND bChar <= 16#66 THEN       // 'a'..'f'
        iDigit := BYTE_TO_INT(bChar) - 16#61 + 10;  // lint:allow STL008 'a' = 10 в шестнадцатеричной записи
    END_IF
    IF iDigit >= 0 THEN
        wResult := SHL(wResult, GVL_C2aConst.NIBBLE_BITS) OR INT_TO_WORD(iDigit);
    END_IF
END_FOR
F_C2aHexStrToWord := wResult;
