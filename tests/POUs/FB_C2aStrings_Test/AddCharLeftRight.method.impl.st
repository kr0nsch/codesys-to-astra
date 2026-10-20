coUnit.TEST('AddCharLeftRight');

sL := F_C2aAddChar(sInputString := '7', usiTargetLen := 3, sAddChar := '0', xRight := FALSE);
sR := F_C2aAddChar(sInputString := 'ab', usiTargetLen := 4, sAddChar := '.', xRight := TRUE);
sLong := F_C2aAddChar(sInputString := 'abcdef', usiTargetLen := 3, sAddChar := '0', xRight := TRUE);
AssertEquals_STRING(Expected := '007', Actual := sL, Message := 'left');
AssertEquals_STRING(Expected := 'ab..', Actual := sR, Message := 'right');
AssertEquals_STRING(Expected := 'abcdef', Actual := sLong, Message := 'longer unchanged');

coUnit.TEST_FINISHED();
