IF xUpperCase THEN
    sDigits := GVL_C2aConst.HEX_DIGITS_UPPER;
ELSE
    sDigits := GVL_C2aConst.HEX_DIGITS_LOWER;
END_IF
sHex := '';
FOR iNibbleNo := GVL_C2aConst.HEX_WORD_DIGITS - 1 TO 0 BY -1 DO
    iNibble := WORD_TO_INT(SHR(wInput, iNibbleNo * GVL_C2aConst.NIBBLE_BITS) AND 16#F);
    sHex := CONCAT(sHex, MID(sDigits, 1, iNibble + 1));
END_FOR
F_C2aWordToHexStr := CONCAT(sPrefix, sHex);
