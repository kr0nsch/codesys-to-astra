fbHeater(PV := GVL_Mx.rTSupply_C, SP := SP_BACKUP_C, HYST := HYST_C, DB := 0.0);
xHeaterOn := fbHeater.HEATER AND GVL_Hmi.eState = E_BoilerState.Fault;
