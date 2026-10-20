// Назначение: распаковка значения из массива регистров канала Modbus REGUL по индексу: REAL (два слова
//             по eOrder), INT, WORD. Индекс вне массива — xValid = FALSE, выходы не меняются.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/IO.md
FUNCTION_BLOCK FB_C2aMbUnpack
VAR_IN_OUT
    awData : ARRAY [*] OF WORD;     // данные канала (Data)
END_VAR
VAR_INPUT
    diIndex : DINT;                 // индекс первого регистра значения
    eOrder : E_C2aWordOrder;        // порядок слов для REAL
END_VAR
VAR_OUTPUT
    rReal : REAL;       // FLOAT32 из awData[diIndex], awData[diIndex + 1]
    iInt : INT;         // INT16 из awData[diIndex]
    wWord : WORD;       // WORD из awData[diIndex]
    xValid : BOOL;      // индекс в границах массива
END_VAR
VAR
    diLow : DINT;       // нижняя граница массива
    diHigh : DINT;      // верхняя граница массива
END_VAR
