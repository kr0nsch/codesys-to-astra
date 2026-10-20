// Назначение: замена узла OwenRTC таргета ПЛК2xx (Targets v3.4, табл. 4.1, с. 10–11) поверх SysTimeRtc:
//             дата и время, форматированные строки (dd.MM.yyyy, hh:mm:ss), Unix time как DT, системный
//             таймер LTIME(). Смещение UTC задаётся входом (на REGUL источник времени и NTP — «Настройка
//             времени»). Каналы установки времени и NTP ОВЕН не повторяются (todo в io-map).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
FUNCTION_BLOCK FB_C2aRtc
VAR_INPUT
    siUtcOffset_h : SINT;   // смещение местного времени от UTC, ч (−12..14, как канал UTC Offset)
END_VAR
VAR_OUTPUT
    uiYear : UINT;              // Year
    usiMonth : USINT;           // Month
    usiDay : USINT;             // Day
    usiHour : USINT;            // Hour
    usiMinute : USINT;          // Minute
    usiSecond : USINT;          // Second
    usiDayOfWeek : USINT;       // Day of week (1 — понедельник)
    sFormatDate : STRING(80);   // Format date: dd.MM.yyyy
    sFormatTime : STRING(80);   // Format time: hh:mm:ss
    dtDateAndTime : DT;         // Date And Time (Unix time)
    ltSystemTimer : LTIME;      // System timer
    xOk : BOOL;                 // время прочитано без ошибки
END_VAR
VAR
    udiResult : UDINT;          // код результата SysTimeRtcGet
    udiUtc : UDINT;             // секунды Unix UTC
    udiLocal : UDINT;           // секунды местного времени
    stDate : ST_C2aDateTime;    // разобранное местное время
END_VAR
