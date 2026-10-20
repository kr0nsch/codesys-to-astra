// Назначение: замена OSU.WORD_TO_HEX_STR (OwenStringUtils v3.0, с. 51): WORD -> строка с префиксом и
//             4 hex-символами (дополнение нулями — допущение A9, сверить с ПЛК210), регистр по xUpperCase.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
FUNCTION F_C2aWordToHexStr : STRING(8)
VAR_INPUT
    wInput : WORD;          // исходное значение
    xUpperCase : BOOL;      // TRUE — верхний регистр hex-символов
    sPrefix : STRING(4);    // префикс строки
END_VAR
VAR
    iNibbleNo : INT;        // номер тетрады от старшей
    iNibble : INT;          // значение тетрады 0..15
    sDigits : STRING(16);   // алфавит hex
    sHex : STRING(8);       // hex-часть
END_VAR
