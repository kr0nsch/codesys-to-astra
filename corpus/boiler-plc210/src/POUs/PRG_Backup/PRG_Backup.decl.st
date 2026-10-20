// Назначение: резервный электрокотёл — двухпозиционный регулятор ON_OFF_HIST_REG (CmpOwenPidRegs).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
PROGRAM PRG_Backup
VAR
    fbHeater : OPR.ON_OFF_HIST_REG; // двухпозиционный регулятор
    xHeaterOn : BOOL;               // включить ТЭН
END_VAR
VAR CONSTANT
    SP_BACKUP_C : REAL := 45.0;     // уставка резерва, °C
    HYST_C : REAL := 2.0;           // гистерезис, °C
END_VAR
