coUnit.TEST('TwoDigitsComma');

sResult := F_C2aRealToStringFormat(3.14159, 2, E_C2aDecimalSeparator.COMMA);
AssertEquals_STRING(Expected := '3,14', Actual := sResult, Message := CONCAT('comma: ', sResult));

coUnit.TEST_FINISHED();
