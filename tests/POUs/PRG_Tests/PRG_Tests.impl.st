coUnit.RUN();
// AreAllTestsFinished() — после RUN(): у метода есть побочный эффект на первом цикле.
xAllFinished := fbStrings.AreAllTestsFinished()
        AND fbRealFormat.AreAllTestsFinished()
        AND fbModbus.AreAllTestsFinished()
        AND fbTime.AreAllTestsFinished()
        AND fbPid.AreAllTestsFinished();
