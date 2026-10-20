// Назначение: состояние котла (вымышленная котельная №3, ПЛК210 — синтетический слой ОВЕН).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
{attribute 'qualified_only'}
TYPE E_BoilerState :
(
    Off := 0,       // остановлен
    Run := 1,       // работа
    Fault := 2      // авария горелки
) INT;
END_TYPE
