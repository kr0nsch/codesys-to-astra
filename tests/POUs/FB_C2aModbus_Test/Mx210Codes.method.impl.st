coUnit.TEST('Mx210Codes');

eBreak := F_C2aMx210Status(16#FD);
eOff := F_C2aMx210Status(16#F7);
eOk := F_C2aMx210Status(16#42);
AssertTrue(Condition := eBreak = E_C2aMx210Status.SensorBreak, Message := 'break');
AssertTrue(Condition := eOff = E_C2aMx210Status.SensorOff, Message := 'off');
AssertTrue(Condition := eOk = E_C2aMx210Status.Ok, Message := 'ok');

coUnit.TEST_FINISHED();
