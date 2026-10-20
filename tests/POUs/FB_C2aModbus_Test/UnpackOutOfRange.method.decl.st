// индекс вне массива -> xValid = FALSE
METHOD PRIVATE UnpackOutOfRange
VAR
    awData : ARRAY [0..1] OF WORD;  // регистры
    fbUnpack : FB_C2aMbUnpack;  // распаковка
END_VAR
