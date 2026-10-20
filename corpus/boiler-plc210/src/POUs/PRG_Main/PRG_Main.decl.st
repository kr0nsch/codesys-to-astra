// Назначение: регулирование подачи (ПИД CmpOwenPidRegs), насос, строки для панели (OwenStringUtils).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
PROGRAM PRG_Main
VAR
    fbPid : OPR.STD_PID;    // ПИД подачи
    rSp_C : REAL;           // уставка подачи, °C
    rValve : REAL;          // выход ПИД 0..1
    fbRunTimer : TON;       // секундный такт наработки
END_VAR
VAR CONSTANT
    XP_C : REAL := 20.0;    // полоса пропорциональности, °C
    TI_S : REAL := 120.0;   // постоянная интегрирования, с
    T_SECOND : TIME := T#1S;    // такт счёта наработки
    DIGITS : USINT := 1;    // знаков после запятой
END_VAR
