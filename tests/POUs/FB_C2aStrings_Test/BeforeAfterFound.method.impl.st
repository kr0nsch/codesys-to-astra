coUnit.TEST('BeforeAfterFound');

sB := F_C2aBefore(sSource := 'key=val=x', sPostfix := '=');
sA := F_C2aAfter(sSource := 'key=val=x', sPrefix := '=');
AssertEquals_STRING(Expected := 'key', Actual := sB, Message := 'before');
AssertEquals_STRING(Expected := 'val=x', Actual := sA, Message := 'after');

coUnit.TEST_FINISHED();
