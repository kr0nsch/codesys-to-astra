coUnit.TEST('HexUpperPadded');

sResult := F_C2aWordToHexStr(wInput := 16#00AF, xUpperCase := TRUE, sPrefix := '0x');
AssertEquals_STRING(Expected := '0x00AF', Actual := sResult, Message := 'upper, padded');

coUnit.TEST_FINISHED();
