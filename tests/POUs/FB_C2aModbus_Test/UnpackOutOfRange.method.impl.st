coUnit.TEST('UnpackOutOfRange');

fbUnpack(awData := awData, diIndex := 5, eOrder := E_C2aWordOrder.HighWordFirst);
AssertFalse(Condition := fbUnpack.xValid, Message := 'out of range');

coUnit.TEST_FINISHED();
