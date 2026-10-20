coUnit.TEST('OutputClampedHigh');

fbHigh(PV := 0.0, SP := 1000.0, XP := 1.0, TI := 0.0, TD := 0.0, PMIN := 0.0, PMAX := 1.0);
iCycHigh := iCycHigh + 1;
IF iCycHigh >= CYCLES_TO_SETTLE THEN
    AssertEquals_REAL(Expected := 1.0, Actual := fbHigh.Y, Delta := R_DELTA,
                      Message := CONCAT('clamp high, Y = ', REAL_TO_STRING(fbHigh.Y)));
    coUnit.TEST_FINISHED();
END_IF
