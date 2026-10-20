// Назначение: программа запуска юнит-тестов CfUnit (coUnit 1.2.0.0) для AstraCompat: объявляет
//             экземпляры наборов (объявление регистрирует набор) и каждый цикл вызывает coUnit.RUN().
//             Назначается задаче только тестового приложения (CODESYS Control Win).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/TEST_REPORT.md
PROGRAM PRG_Tests
VAR
    fbStrings : FB_C2aStrings_Test;     // строки OwenStringUtils
    fbRealFormat : FB_C2aRealFormat_Test;   // REAL_TO_STRING_FORMAT
    fbModbus : FB_C2aModbus_Test;       // распаковка Modbus
    fbTime : FB_C2aTime_Test;           // календарь и OwenRTC
    fbPid : FB_C2aPid_Test;             // ПИД
    // все наборы завершены — флаг для скрипта запуска тестов (read_value)
    xAllFinished : BOOL;
END_VAR
