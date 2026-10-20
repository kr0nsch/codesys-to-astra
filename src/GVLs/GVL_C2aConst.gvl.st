// Назначение: константы AstraCompat.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
{attribute 'qualified_only'}
VAR_GLOBAL CONSTANT
    SECONDS_PER_DAY : UDINT := 86400;   // секунд в сутках
    SECONDS_PER_HOUR : DINT := 3600;    // секунд в часе
    HEX_DIGITS_UPPER : STRING(16) := '0123456789ABCDEF';
    HEX_DIGITS_LOWER : STRING(16) := '0123456789abcdef';
    HEX_WORD_DIGITS : INT := 4;         // hex-символов в WORD
    NIBBLE_BITS : INT := 4;             // бит в тетраде
    MAX_FRACTION_DIGITS : USINT := 7;   // знаков после разделителя в F_C2aRealToStringFormat
    EXP_THRESHOLD : REAL := 1.0E8;      // выше — экспоненциальная запись (OwenStringUtils v3.0, с. 9)
END_VAR
