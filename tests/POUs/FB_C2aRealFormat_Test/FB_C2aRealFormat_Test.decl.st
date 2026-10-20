// Назначение: тесты F_C2aRealToStringFormat (OwenStringUtils v3.0, с. 9): знаки, разделитель, знак, ноль.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/TEST_REPORT.md
FUNCTION_BLOCK FB_C2aRealFormat_Test EXTENDS coUnit.FB_TestSuite
VAR CONSTANT
    R_DELTA : REAL := 0.0001;   // допуск сравнения REAL
END_VAR
