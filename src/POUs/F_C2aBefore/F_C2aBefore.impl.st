iPos := FIND(sSource, sPostfix);
IF iPos > 0 AND LEN(sPostfix) > 0 THEN
    F_C2aBefore := LEFT(sSource, iPos - 1);
ELSE
    F_C2aBefore := '';
END_IF
