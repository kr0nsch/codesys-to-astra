// Назначение: время ПЛК из каналов узла OwenRTC и данные узла Watchdog.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
VAR_GLOBAL
    dtNow : DT;             // Date And Time
    sDateText : STRING(80); // Format date
    sTimeText : STRING(80); // Format time
    usiHour : USINT;        // Hour
    usiWeek : USINT;        // Week of year
    udiLastExc : UDINT;     // Watchdog: код последнего исключения
END_VAR
