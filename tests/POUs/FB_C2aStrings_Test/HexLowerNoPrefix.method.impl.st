coUnit.TEST('HexLowerNoPrefix');

sResult := F_C2aWordToHexStr(wInput := 16#BEEF, xUpperCase := FALSE, sPrefix := '');
AssertEquals_STRING(Expected := 'beef', Actual := sResult, Message := 'lower');

coUnit.TEST_FINISHED();
