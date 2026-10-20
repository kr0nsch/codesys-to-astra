coUnit.TEST('Concat4');

sResult := F_C2aConcat4('T=', '21', ',', '5');
AssertEquals_STRING(Expected := 'T=21,5', Actual := sResult, Message := 'concat4');

coUnit.TEST_FINISHED();
