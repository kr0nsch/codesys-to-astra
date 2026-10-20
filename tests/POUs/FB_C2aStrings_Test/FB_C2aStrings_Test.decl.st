// Назначение: набор тестов строковых замен OwenStringUtils (ожидания — по описанию ОВЕН v3.0, а не по коду).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/TEST_REPORT.md
FUNCTION_BLOCK FB_C2aStrings_Test EXTENDS coUnit.FB_TestSuite
VAR CONSTANT
    R_DELTA : REAL := 0.0001;   // допуск сравнения REAL
END_VAR
