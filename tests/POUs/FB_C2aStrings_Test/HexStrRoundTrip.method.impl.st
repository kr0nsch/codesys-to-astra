coUnit.TEST('HexStrRoundTrip');

wResult := F_C2aHexStrToWord(sInputString := '0x1A2b', sPrefix := '0x');
AssertEquals_WORD(Expected := 16#1A2B, Actual := wResult, Message := 'hex parse');

coUnit.TEST_FINISHED();
