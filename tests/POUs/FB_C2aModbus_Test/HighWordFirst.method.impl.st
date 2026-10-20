coUnit.TEST('HighWordFirst');

rResult := F_C2aMbToReal(16#41A0, 16#0000, E_C2aWordOrder.HighWordFirst);
AssertEquals_REAL(Expected := 20.0, Actual := rResult, Delta := R_DELTA, Message := 'hi first');

coUnit.TEST_FINISHED();
