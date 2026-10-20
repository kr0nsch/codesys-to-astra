// Назначение: отопительный график: уставка подачи по наружной температуре (линейно, с ограничением).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
FUNCTION F_HeatingCurve : REAL
VAR_INPUT
    rTOutdoor_C : REAL;     // наружная температура, °C
    rSpBase_C : REAL;       // уставка при 0 °C
END_VAR
VAR CONSTANT
    SLOPE : REAL := -1.2;   // наклон графика, °C/°C
    SP_MIN : REAL := 35.0;  // минимум подачи, °C
    SP_MAX : REAL := 95.0;  // максимум подачи, °C
END_VAR
