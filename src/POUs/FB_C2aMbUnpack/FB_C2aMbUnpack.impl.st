diLow := LOWER_BOUND(awData, 1);
diHigh := UPPER_BOUND(awData, 1);
xValid := diIndex >= diLow AND diIndex <= diHigh;
IF xValid THEN
    wWord := awData[diIndex];
    iInt := WORD_TO_INT(awData[diIndex]);
    IF diIndex + 1 <= diHigh THEN
        rReal := F_C2aMbToReal(awData[diIndex], awData[diIndex + 1], eOrder);
    END_IF
END_IF
