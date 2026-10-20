// Назначение: замена OSU.HEX_STR_TO_WORD (OwenStringUtils v3.0, с. 50): строка с префиксом (до 4 символов)
//             и hex-значением (до 4 символов, регистр не важен) -> WORD. Строка не валидируется, как у ОВЕН:
//             символы вне 0..9, A..F пропускаются.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
FUNCTION F_C2aHexStrToWord : WORD
VAR_INPUT
    sInputString : STRING(8);   // строка с HEX-значением
    sPrefix : STRING(4);        // префикс исходной строки ('' — без префикса)
END_VAR
VAR
    sValue : STRING(8);     // строка без префикса
    iChar : INT;            // индекс символа (с 0)
    bChar : BYTE;           // код символа
    wResult : WORD;         // накопленное значение
    iDigit : INT;           // значение символа или -1
END_VAR
