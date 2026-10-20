// Назначение: сохраняемые уставки и наработка.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
VAR_GLOBAL RETAIN
    rSpBase_C : REAL := 70.0;   // базовая уставка подачи, °C
    udiRunTime_s : UDINT;       // наработка насоса, с
END_VAR
