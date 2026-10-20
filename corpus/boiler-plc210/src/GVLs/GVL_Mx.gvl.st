// Назначение: значения модулей Mx210 (привязки к каналам шаблонов МВ210-101 и МУ210-402 в дереве устройств).
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   corpus/boiler-plc210/README.md
VAR_GLOBAL
    rTSupply_C : REAL;      // температура подачи, °C (МВ210-101, вход 1)
    rTReturn_C : REAL;      // температура обратки, °C (вход 2)
    rTOutdoor_C : REAL;     // температура наружного воздуха, °C (вход 3)
    iTSupplyRaw : INT;      // подача, целое (вход 1, integer)
    wDoMask : WORD;         // выходы МУ210-402 (битовая маска)
    wMeterStatus : WORD;    // счётчик энергии на Modbus 3S (канал FC 23)
END_VAR
