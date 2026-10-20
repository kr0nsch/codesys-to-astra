coUnit.TEST('RoundsHalfUp');

s0 := F_C2aRealToStringFormat(2.5, 0, E_C2aDecimalSeparator.DOT);
s2 := F_C2aRealToStringFormat(0.125, 2, E_C2aDecimalSeparator.DOT);
AssertEquals_STRING(Expected := '3', Actual := s0, Message := 'half up');
AssertEquals_STRING(Expected := '0.13', Actual := s2, Message := 'half up frac');

coUnit.TEST_FINISHED();
