sHex := F_C2aWordToHexStr(wInput := 16#BEEF, xUpperCase := TRUE, sPrefix := '0x');
wValue := F_C2aHexStrToWord(sInputString := sHex, sPrefix := '0x');
sText := F_C2aConcat4(F_C2aBefore('a=b', '='), F_C2aAfter('a=b', '='), F_C2aAddChar('7', 3, '0', FALSE), '');
sReal := F_C2aRealToStringFormat(rValueToConvert := 3.14159, usiSignificantDigitsCount := 2,
                                 eDecimalSeparator := E_C2aDecimalSeparator.COMMA);
rValue := F_C2aMbToReal(awData[0], awData[1], E_C2aWordOrder.HighWordFirst);
fbUnpack(awData := awData, diIndex := 0, eOrder := E_C2aWordOrder.HighWordFirst);
eStatus := F_C2aMx210Status(16#FD);
fbRtc(siUtcOffset_h := 3);
fbPid(PV := 20.0, SP := 21.0, XP := 10.0, TI := 60.0, TD := 0.0, PMIN := 0.0, PMAX := 1.0);
