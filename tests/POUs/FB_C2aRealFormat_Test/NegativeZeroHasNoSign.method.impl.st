coUnit.TEST('NegativeZeroHasNoSign');

sResult := F_C2aRealToStringFormat(-0.0001, 2, E_C2aDecimalSeparator.DOT);
AssertEquals_STRING(Expected := '0.00', Actual := sResult, Message := CONCAT('no minus zero: ', sResult));

coUnit.TEST_FINISHED();
