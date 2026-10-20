coUnit.TEST('UnpackInRange');

fbUnpack(awData := awData, diIndex := 0, eOrder := E_C2aWordOrder.HighWordFirst);
AssertEquals_REAL(Expected := -100.0, Actual := fbUnpack.rReal, Delta := R_DELTA, Message := 'real');
fbUnpack(awData := awData, diIndex := 2, eOrder := E_C2aWordOrder.HighWordFirst);
AssertEquals_INT(Expected := -2, Actual := fbUnpack.iInt, Message := 'int');
AssertTrue(Condition := fbUnpack.xValid, Message := 'valid');

coUnit.TEST_FINISHED();
