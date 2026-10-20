// FB_C2aMbUnpack: REAL и INT по индексу
METHOD PRIVATE UnpackInRange
VAR
    awData : ARRAY [0..3] OF WORD := [16#C2C8, 16#0000, 16#FFFE, 0];  // -100.0, -2
    fbUnpack : FB_C2aMbUnpack;  // распаковка
END_VAR
