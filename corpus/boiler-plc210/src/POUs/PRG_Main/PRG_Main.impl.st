rSp_C := F_HeatingCurve(GVL_Mx.rTOutdoor_C, GVL_Persist.rSpBase_C);
fbPid(PV := GVL_Mx.rTSupply_C, SP := rSp_C, XP := XP_C, TI := TI_S, TD := 0.0, PMIN := 0.0, PMAX := 1.0,
      Y_MAN_SET := FALSE, Y_MANUAL := 0.0);
rValve := fbPid.Y;
IF GVL_Hmi.eState <> E_BoilerState.Fault THEN
    GVL_Hmi.eState := E_BoilerState.Run;
END_IF
GVL_Hw.xPumpRun := GVL_Hmi.eState = E_BoilerState.Run;
GVL_Mx.wDoMask := SEL(GVL_Hw.xPumpRun, 16#0000, 16#0001);
fbRunTimer(IN := GVL_Hw.xPumpRun AND NOT fbRunTimer.Q, PT := T_SECOND);
IF fbRunTimer.Q THEN
    GVL_Persist.udiRunTime_s := GVL_Persist.udiRunTime_s + 1;
END_IF
GVL_Hmi.sStatus := OSU.CONCAT4('T=', OSU.REAL_TO_STRING_FORMAT(GVL_Mx.rTSupply_C, DIGITS, OSU.DECIMAL_SEPARATOR.COMMA),
                               ' C, SP=', OSU.REAL_TO_STRING_FORMAT(rSp_C, DIGITS, OSU.DECIMAL_SEPARATOR.COMMA));
GVL_Hmi.sCode := OSU.WORD_TO_HEX_STR(wInput := GVL_Hw.wHmiStatus, xUpperCase := TRUE, sPrefix := '0x');
