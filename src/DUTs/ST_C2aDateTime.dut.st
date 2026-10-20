// Назначение: дата и время по каналам узла OwenRTC (Targets v3.4, табл. 4.1, с. 10–11).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
TYPE ST_C2aDateTime :
STRUCT
    uiYear : UINT;          // год
    usiMonth : USINT;       // месяц 1..12
    usiDay : USINT;         // день 1..31
    usiHour : USINT;        // час 0..23
    usiMinute : USINT;      // минута 0..59
    usiSecond : USINT;      // секунда 0..59
    usiDayOfWeek : USINT;   // день недели: 1 — понедельник, 7 — воскресенье
END_STRUCT
END_TYPE
