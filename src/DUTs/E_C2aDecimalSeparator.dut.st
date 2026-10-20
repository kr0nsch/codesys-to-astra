// Назначение: разделитель целой и дробной части для F_C2aRealToStringFormat — аналог
//             перечисления DECIMAL_SEPARATOR OwenStringUtils (DOT = 0, COMMA = 1, USINT; документ ОВЕН v3.0,
//             табл. 3.2.2, с. 9).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_C2aDecimalSeparator :
(
    DOT := 0,       // точка
    COMMA := 1      // запятая
) USINT;
END_TYPE
