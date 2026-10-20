// Назначение: медленная задача (приоритет 15 у ОВЕН): слово состояния панели.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
PROGRAM PRG_Slow
VAR
END_VAR
VAR CONSTANT
    BIT_FAULT : WORD := 16#0002;    // бит «авария» в слове состояния
    BIT_RUN : WORD := 16#0001;      // бит «работа»
END_VAR
