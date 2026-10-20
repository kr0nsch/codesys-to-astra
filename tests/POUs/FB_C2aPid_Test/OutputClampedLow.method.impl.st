coUnit.TEST('OutputClampedLow');

fbLow(PV := 1000.0, SP := 0.0, XP := 1.0, TI := 0.0, TD := 0.0, PMIN := -0.5, PMAX := 1.0);
iCycLow := iCycLow + 1;
IF iCycLow >= CYCLES_TO_SETTLE THEN
    AssertEquals_REAL(Expected := -0.5, Actual := fbLow.Y, Delta := R_DELTA,
                      Message := CONCAT('clamp low, Y = ', REAL_TO_STRING(fbLow.Y)));
    coUnit.TEST_FINISHED();
END_IF
