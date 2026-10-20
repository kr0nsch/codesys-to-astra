IF XP > 0.0 THEN
    rKp := 1.0 / XP;
ELSE
    rKp := 0.0;
END_IF
// TI = 0 — без интегральной составляющей: Util.PID при TN = 0 уходит в OVERFLOW и останавливается
// (документация Util 3.5.17.0), поэтому ПД-регулятор Util.PD
IF TI > 0.0 THEN
    fbPid(ACTUAL := PV, SET_POINT := SP, KP := rKp, TN := TI, TV := TD, Y_MANUAL := Y_MANUAL, Y_OFFSET := 0.0,
          Y_MIN := PMIN, Y_MAX := PMAX, MANUAL := Y_MAN_SET, RESET := FALSE);
    rY := fbPid.Y;
ELSE
    fbPd(ACTUAL := PV, SET_POINT := SP, KP := rKp, TV := TD, Y_MANUAL := Y_MANUAL, Y_OFFSET := 0.0,
         Y_MIN := PMIN, Y_MAX := PMAX, MANUAL := Y_MAN_SET, RESET := FALSE);
    rY := fbPd.Y;
END_IF
Y := LIMIT(PMIN, rY, PMAX);
