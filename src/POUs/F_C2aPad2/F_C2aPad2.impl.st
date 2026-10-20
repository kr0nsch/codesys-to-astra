IF usiValue < 10 THEN  // lint:allow STL008 одна десятичная цифра
    F_C2aPad2 := CONCAT('0', USINT_TO_STRING(usiValue));
ELSE
    F_C2aPad2 := USINT_TO_STRING(usiValue MOD 100);  // lint:allow STL008 две десятичные цифры
END_IF
