coUnit.TEST('Epoch');

stD := F_C2aUnixToDate(0);
AssertEquals_UINT(Expected := 1970, Actual := stD.uiYear, Message := 'year');
AssertEquals_USINT(Expected := 1, Actual := stD.usiMonth, Message := 'month');
AssertEquals_USINT(Expected := 1, Actual := stD.usiDay, Message := 'day');
AssertEquals_USINT(Expected := 4, Actual := stD.usiDayOfWeek, Message := 'thursday');

coUnit.TEST_FINISHED();
