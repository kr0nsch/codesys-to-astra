coUnit.TEST('ManualPassesThrough');

fbManual(Y_MANUAL := 0.4, Y_MAN_SET := TRUE, PV := 10.0, SP := 50.0, XP := 10.0, TI := 0.0, TD := 0.0,
         PMIN := 0.0, PMAX := 1.0);
iCycManual := iCycManual + 1;
IF iCycManual >= CYCLES_TO_SETTLE THEN
    AssertEquals_REAL(Expected := 0.4, Actual := fbManual.Y, Delta := R_DELTA,
                      Message := CONCAT('manual, Y = ', REAL_TO_STRING(fbManual.Y)));
    coUnit.TEST_FINISHED();
END_IF
