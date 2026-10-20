// Назначение: два регистра Modbus (канал REGUL — ARRAY OF WORD, DPA-302.1 с. 15–16) -> REAL по порядку слов.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/IO.md
FUNCTION F_C2aMbToReal : REAL
VAR_INPUT
    wFirst : WORD;              // первый регистр блока
    wSecond : WORD;             // второй регистр блока
    eOrder : E_C2aWordOrder;    // порядок слов
END_VAR
VAR
    uValue : U_C2aReal32;       // 32 бита как REAL/DWORD
END_VAR
