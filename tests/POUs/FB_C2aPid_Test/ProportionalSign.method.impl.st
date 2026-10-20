coUnit.TEST('ProportionalSign');

fbSign(PV := 20.0, SP := 21.0, XP := 10.0, TI := 0.0, TD := 0.0, PMIN := -1.0, PMAX := 1.0);
iCycSign := iCycSign + 1;
IF iCycSign >= CYCLES_TO_SETTLE THEN
    AssertTrue(Condition := fbSign.Y > 0.0 AND fbSign.Y <= 1.0,
               Message := CONCAT('positive, Y = ', REAL_TO_STRING(fbSign.Y)));
    coUnit.TEST_FINISHED();
END_IF
