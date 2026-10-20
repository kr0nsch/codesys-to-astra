// Назначение: встроенный ввод-вывод ПЛК210 по AT-адресам (так делать ОВЕН не рекомендует — Targets v3.4, разд. 1;
//             вход нарочно с AT, чтобы показать C2A-IO001).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
VAR_GLOBAL
    xBurner1Fault AT %IX0.0 : BOOL;     // авария горелки К1
    xBurner2Fault AT %IX0.1 : BOOL;     // авария горелки К2
    xPumpRun AT %QX0.0 : BOOL;          // пуск сетевого насоса Н1
    xAlarmHorn AT %QX0.1 : BOOL;        // сирена
    wHmiStatus AT %MW10 : WORD;         // слово состояния для панели
END_VAR
