// Назначение: точка входа рабочей сборки AstraCompat (cds.py build): вызывает функции и ФБ библиотеки,
//             чтобы компилятор собрал всё в обеих IDE. В библиотеку не входит.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/ARCHITECTURE.md
PROGRAM PRG_C2aSelfTest
VAR
    sHex : STRING(8);               // F_C2aWordToHexStr
    wValue : WORD;                  // F_C2aHexStrToWord
    sText : STRING(255);            // строковые функции
    sReal : STRING(80);             // F_C2aRealToStringFormat
    rValue : REAL;                  // F_C2aMbToReal
    awData : ARRAY [0..3] OF WORD;  // регистры
    fbUnpack : FB_C2aMbUnpack;      // распаковка
    eStatus : E_C2aMx210Status;     // статус МВ210
    fbRtc : FB_C2aRtc;              // время
    fbPid : FB_C2aPid;              // ПИД
END_VAR
