coUnit.TEST('RtcReadsClock');

fbRtc(siUtcOffset_h := 0);
AssertTrue(Condition := fbRtc.xOk, Message := 'ok');
AssertTrue(Condition := fbRtc.uiYear >= 2024, Message := 'year plausible');
AssertEquals_UINT(Expected := 10, Actual := INT_TO_UINT(LEN(fbRtc.sFormatDate)), Message := 'dd.MM.yyyy');

coUnit.TEST_FINISHED();
