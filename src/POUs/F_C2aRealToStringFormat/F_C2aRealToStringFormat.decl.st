// Назначение: замена OSU.REAL_TO_STRING_FORMAT (OwenStringUtils v3.0, с. 9): REAL -> строка с заданным
//             числом знаков после разделителя (точка или запятая; недопустимый разделитель — точка).
//             |значение| > 1e8 — экспоненциальная запись REAL_TO_STRING. Округление последнего знака может
//             отличаться от ОВЕН (обёртка, исход check).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
FUNCTION F_C2aRealToStringFormat : STRING(80)
VAR_INPUT
    rValueToConvert : REAL;                     // значение
    usiSignificantDigitsCount : USINT;          // знаков после разделителя (0..7)
    eDecimalSeparator : E_C2aDecimalSeparator;  // разделитель
END_VAR
VAR
    usiDigits : USINT;      // знаков после разделителя после ограничения
    lrAbs : LREAL;          // модуль значения
    lrScaled : LREAL;       // модуль · 10^usiDigits + 0.5
    uliPow : ULINT;          // 10 ^ usiDigits
    uliScaled : ULINT;       // модуль, умноженный на 10 ^ usiDigits и округлённый
    uliInt : ULINT;          // целая часть
    uliFrac : ULINT;         // дробная часть
    sFrac : STRING(80);     // дробная часть строкой
    sSep : STRING(1);       // разделитель
    usiIdx : USINT;         // счётчик
END_VAR
