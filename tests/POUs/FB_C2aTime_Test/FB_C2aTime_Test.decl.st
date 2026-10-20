// Назначение: тесты календаря F_C2aUnixToDate и форматов FB_C2aRtc (ожидания — по календарю, не по коду).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/TEST_REPORT.md
FUNCTION_BLOCK FB_C2aTime_Test EXTENDS coUnit.FB_TestSuite
VAR CONSTANT
    R_DELTA : REAL := 0.0001;   // допуск сравнения REAL
END_VAR
