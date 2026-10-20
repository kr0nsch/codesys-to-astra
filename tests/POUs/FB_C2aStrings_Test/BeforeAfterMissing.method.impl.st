coUnit.TEST('BeforeAfterMissing');

sB := F_C2aBefore(sSource := 'abc', sPostfix := ';');
sA := F_C2aAfter(sSource := 'abc', sPrefix := ';');
AssertEquals_STRING(Expected := '', Actual := sB, Message := 'before missing');
AssertEquals_STRING(Expected := '', Actual := sA, Message := 'after missing');

coUnit.TEST_FINISHED();
