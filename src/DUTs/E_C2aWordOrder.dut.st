// Назначение: порядок слов 32-битного значения в двух регистрах Modbus (канал REGUL отдаёт
//             ARRAY OF WORD, DPA-302.1 с. 15–16). Порядок слов FLOAT32 Mx210 через драйвер REGUL не сверен —
//             docs/HARDWARE_VALIDATION.md.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/IO.md
{attribute 'qualified_only'}
TYPE E_C2aWordOrder :
(
    HighWordFirst := 0,     // старшее слово в первом регистре
    LowWordFirst := 1       // младшее слово в первом регистре
) USINT;
END_TYPE
