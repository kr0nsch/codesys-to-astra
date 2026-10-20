IF eOrder = E_C2aWordOrder.LowWordFirst THEN
    uValue.dwValue := SHL(WORD_TO_DWORD(wSecond), 16) OR WORD_TO_DWORD(wFirst);  // lint:allow STL008 16 бит слова
ELSE
    uValue.dwValue := SHL(WORD_TO_DWORD(wFirst), 16) OR WORD_TO_DWORD(wSecond);  // lint:allow STL008 16 бит слова
END_IF
F_C2aMbToReal := uValue.rValue;
