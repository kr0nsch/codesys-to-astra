coUnit.TEST('TimeOfDay');

stD := F_C2aUnixToDate(1792494245);
AssertEquals_UINT(Expected := 2026, Actual := stD.uiYear, Message := 'year');
AssertEquals_USINT(Expected := 10, Actual := stD.usiMonth, Message := 'month');
AssertEquals_USINT(Expected := 20, Actual := stD.usiDay, Message := 'day');
AssertEquals_USINT(Expected := 11, Actual := stD.usiHour, Message := 'hour');
AssertEquals_USINT(Expected := 4, Actual := stD.usiMinute, Message := 'minute');
AssertEquals_USINT(Expected := 5, Actual := stD.usiSecond, Message := 'second');
AssertEquals_USINT(Expected := 2, Actual := stD.usiDayOfWeek, Message := 'tuesday');

coUnit.TEST_FINISHED();
