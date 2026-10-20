// Назначение: детерминированные свойства FB_C2aPid: ручной режим, ограничения выхода, знак П-звена.
//             Алгоритм ОВЕН STD_PID не повторяется (обёртка над Util.PID, исход check). Util.PID считает
//             по времени между вызовами, поэтому экземпляры живут в наборе, а проверка — через
//             CYCLES_TO_SETTLE циклов задачи.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/TEST_REPORT.md
FUNCTION_BLOCK FB_C2aPid_Test EXTENDS coUnit.FB_TestSuite
VAR CONSTANT
    R_DELTA : REAL := 0.0001;       // допуск сравнения REAL
    CYCLES_TO_SETTLE : INT := 5;    // циклов до проверки
END_VAR
VAR
    fbManual : FB_C2aPid;   // ручной режим
    fbHigh : FB_C2aPid;     // насыщение сверху
    fbLow : FB_C2aPid;      // насыщение снизу
    fbSign : FB_C2aPid;     // знак П-звена
    iCycManual : INT;       // счётчик циклов теста ManualPassesThrough
    iCycHigh : INT;         // счётчик циклов теста OutputClampedHigh
    iCycLow : INT;          // счётчик циклов теста OutputClampedLow
    iCycSign : INT;         // счётчик циклов теста ProportionalSign
END_VAR
