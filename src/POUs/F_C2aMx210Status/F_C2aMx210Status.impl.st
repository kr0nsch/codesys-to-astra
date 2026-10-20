CASE bCode OF
    16#F0: F_C2aMx210Status := E_C2aMx210Status.Invalid;
    16#F6: F_C2aMx210Status := E_C2aMx210Status.NotReady;
    16#F7: F_C2aMx210Status := E_C2aMx210Status.SensorOff;
    16#F8: F_C2aMx210Status := E_C2aMx210Status.ColdJunctionHigh;
    16#F9: F_C2aMx210Status := E_C2aMx210Status.ColdJunctionLow;
    16#FA: F_C2aMx210Status := E_C2aMx210Status.TooHigh;
    16#FB: F_C2aMx210Status := E_C2aMx210Status.TooLow;
    16#FC: F_C2aMx210Status := E_C2aMx210Status.ShortCircuit;
    16#FD: F_C2aMx210Status := E_C2aMx210Status.SensorBreak;
    16#FE: F_C2aMx210Status := E_C2aMx210Status.AdcFailure;
    16#FF: F_C2aMx210Status := E_C2aMx210Status.BadCalibration;
ELSE
    F_C2aMx210Status := E_C2aMx210Status.Ok;
END_CASE
