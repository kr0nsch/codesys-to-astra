coUnit.TEST('NegativeAndPadding');

sResult := F_C2aRealToStringFormat(-1.05, 3, E_C2aDecimalSeparator.DOT);
AssertEquals_STRING(Expected := '-1.050', Actual := sResult, Message := 'negative padded');

coUnit.TEST_FINISHED();
