// Назначение: тесты распаковки регистров Modbus REGUL: порядок слов FLOAT32, индекс вне массива, статусы МВ210.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/TEST_REPORT.md
FUNCTION_BLOCK FB_C2aModbus_Test EXTENDS coUnit.FB_TestSuite
VAR CONSTANT
    R_DELTA : REAL := 0.0001;   // допуск сравнения REAL
END_VAR
