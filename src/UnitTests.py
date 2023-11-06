import unittest
from Bot import *
from Core import *
from Calendar import *


class MyTestCase(unittest.TestCase):
    def test_something(self):
        tst = "/addevent October 31 2023 20:00:00 Brown Fellows Meeting"
        self.assertEqual(convert_event_message_to_time(tst), ("Brown Fellows Meeting", datetime.datetime(2023, 10, 31, 20, 00)), msg="Wrong")  # add assertion here


if __name__ == '__main__':
    unittest.main()
