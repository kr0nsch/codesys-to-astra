coUnit.TEST('Pad2');

s7 := F_C2aPad2(7);
s42 := F_C2aPad2(42);
AssertEquals_STRING(Expected := '07', Actual := s7, Message := 'pad');
AssertEquals_STRING(Expected := '42', Actual := s42, Message := 'no pad');

coUnit.TEST_FINISHED();
