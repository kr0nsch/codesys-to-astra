IF GVL_Hw.xBurner1Fault OR GVL_Hw.xBurner2Fault THEN
    GVL_Hmi.eState := E_BoilerState.Fault;
    GVL_Hw.xAlarmHorn := TRUE;
ELSE
    GVL_Hw.xAlarmHorn := FALSE;
END_IF
