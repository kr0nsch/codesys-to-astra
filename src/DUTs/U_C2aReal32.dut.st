// Назначение: 32 бита как REAL или DWORD — распаковка FLOAT32 из двух регистров Modbus.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/IO.md
TYPE U_C2aReal32 :
UNION
    rValue : REAL;      // значение с плавающей точкой
    dwValue : DWORD;    // то же как 32 бита
END_UNION
END_TYPE
