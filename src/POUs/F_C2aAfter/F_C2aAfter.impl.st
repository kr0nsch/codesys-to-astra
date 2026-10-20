iPos := FIND(sSource, sPrefix);
IF iPos > 0 AND LEN(sPrefix) > 0 THEN
    F_C2aAfter := RIGHT(sSource, LEN(sSource) - iPos - LEN(sPrefix) + 1);
ELSE
    F_C2aAfter := '';
END_IF
