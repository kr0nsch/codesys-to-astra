// Назначение: строки и коды для панели оператора.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
VAR_GLOBAL
    sStatus : STRING(255);  // строка состояния
    sCode : STRING(8);      // код состояния (hex)
    eState : E_BoilerState; // состояние котла К1
END_VAR
