// Назначение: замена OSU.After (OwenStringUtils v3.0, с. 19): фрагмент sSource после первого вхождения
//             sPrefix; не найдено — пустая строка.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
FUNCTION F_C2aAfter : STRING(255)
VAR_INPUT
    sSource : STRING(255);  // исходная строка
    sPrefix : STRING(255);  // подстрока
END_VAR
VAR
    iPos : INT;             // позиция вхождения (с 1) или 0
END_VAR
