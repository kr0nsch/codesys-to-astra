// Назначение: число 0..99 -> две цифры с ведущим нулём (для форматов даты и времени FB_C2aRtc).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
FUNCTION F_C2aPad2 : STRING(2)
VAR_INPUT
    usiValue : USINT;   // значение 0..99
END_VAR
