// Назначение: секунды Unix (UTC) -> дата и время (григорианский календарь, алгоритм «civil from days»
//             H. Hinnant), день недели по ISO 8601 (1 — понедельник). Чистая функция — тестируется coUnit.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
FUNCTION F_C2aUnixToDate : ST_C2aDateTime
VAR_INPUT
    udiUnix : UDINT;    // секунды с 1970-01-01 00:00:00
END_VAR
VAR
    diDays : DINT;      // сутки с 1970-01-01
    udiSec : UDINT;     // секунды в сутках
    diZ : DINT;         // сутки от 0000-03-01
    diEra : DINT;       // эра (400 лет)
    diDoe : DINT;       // день эры
    diYoe : DINT;       // год эры
    diDoy : DINT;       // день года (от 1 марта)
    diMp : DINT;        // месяц от марта
    diYear : DINT;      // год
    diMonth : DINT;     // месяц
END_VAR
