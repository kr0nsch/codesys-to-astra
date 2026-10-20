coUnit.TEST('LowWordFirst');

rResult := F_C2aMbToReal(16#0000, 16#41A0, E_C2aWordOrder.LowWordFirst);
AssertEquals_REAL(Expected := 20.0, Actual := rResult, Delta := R_DELTA, Message := 'lo first');

coUnit.TEST_FINISHED();
