// Назначение: замена OSU.ADD_CHAR (OwenStringUtils v3.0, с. 33): дополнение sInputString символом sAddChar
//             до длины usiTargetLen справа (xRight) или слева; длиннее — без изменений.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
FUNCTION F_C2aAddChar : STRING(255)
VAR_INPUT
    sInputString : STRING(255); // исходная строка
    usiTargetLen : USINT;       // длина результата
    sAddChar : STRING(1);       // символ-заполнитель
    xRight : BOOL;              // TRUE — справа, FALSE — слева
END_VAR
VAR
    sResult : STRING(255);  // результат
    iGuard : INT;           // защита от бесконечного цикла при пустом sAddChar
END_VAR
