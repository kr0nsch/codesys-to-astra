GVL_Hw.wHmiStatus := 0;
IF GVL_Hmi.eState = E_BoilerState.Run THEN
    GVL_Hw.wHmiStatus := GVL_Hw.wHmiStatus OR BIT_RUN;
END_IF
IF GVL_Hmi.eState = E_BoilerState.Fault THEN
    GVL_Hw.wHmiStatus := GVL_Hw.wHmiStatus OR BIT_FAULT;
END_IF
