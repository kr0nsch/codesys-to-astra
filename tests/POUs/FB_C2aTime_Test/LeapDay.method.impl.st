coUnit.TEST('LeapDay');

stD := F_C2aUnixToDate(951782400);
AssertEquals_UINT(Expected := 2000, Actual := stD.uiYear, Message := 'year');
AssertEquals_USINT(Expected := 2, Actual := stD.usiMonth, Message := 'month');
AssertEquals_USINT(Expected := 29, Actual := stD.usiDay, Message := 'day');
AssertEquals_USINT(Expected := 2, Actual := stD.usiDayOfWeek, Message := 'tuesday');

coUnit.TEST_FINISHED();
