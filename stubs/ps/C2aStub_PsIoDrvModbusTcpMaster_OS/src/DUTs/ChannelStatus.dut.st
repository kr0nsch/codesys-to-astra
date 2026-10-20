// Назначение: заглушка типа статуса канала Modbus драйвера РегЛаб для сборки в CODESYS 3.5.17.30 (в выход не
//             попадает). Имена значений — DPA-302.1 v1.7, с. 15–16 (Unreliable, InProcess, Timeout, Ok,
//             ErrorInResponse, UserReqArg, StopReading); числовые значения в документе не приведены — порядок
//             условный. В Astra.IDE код собирается против настоящей библиотеки PsIoDrvModbusTcpMaster_OS.
// Автор:      kr0nsch
// Версия:     0.1.0
// Документ:   docs/LIBMAP.md
{attribute 'qualified_only'}
TYPE ChannelStatus :
(
    Unreliable,         // данные недостоверны
    InProcess,          // запрос выполняется
    Timeout,            // нет ответа
    Ok,                 // ответ получен
    ErrorInResponse,    // ответ с ошибкой
    UserReqArg,         // ошибка аргументов пользовательского запроса
    StopReading         // опрос остановлен
);
END_TYPE
