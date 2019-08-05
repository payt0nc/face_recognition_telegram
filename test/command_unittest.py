# pylint: disable=duplicate-code, too-many-statements
''' Unit test for basic commands '''
import unittest
import logging
from test.common import async_test, BaseTestCase

# Initialize loggers
logging.basicConfig(level=logging.WARNING)


class TestCommand(BaseTestCase):
    ''' Test basic commands '''

    @async_test
    async def test_start(self):
        ''' Test start command '''
        user = self.user
        await user.send_message('/start')
        message = await user.get_message()
        self.assertTrue(message is not None)
        self.assertTrue('To predict' in message.text)

    @async_test
    async def test_help(self):
        ''' Test help command '''
        user = self.user
        await user.send_message('/help')
        message = await user.get_message()
        self.assertTrue(message is not None)
        self.assertTrue('To predict' in message.text)

    @async_test
    async def test_train_empty(self):
        ''' Test train command with empty argument '''
        user = self.user
        await user.send_message('/train')
        message = await user.get_message()
        self.assertTrue(message is not None)
        self.assertTrue('/train' in message.text)
        self.assertTrue('Example' in message.text)

    @async_test
    async def test_train_tag(self):
        ''' Test train command with tag '''
        user = self.user
        tag = 'test123'
        # Test /train <tag>
        await user.send_message('/train {}'.format(tag))
        message = await user.get_message()
        self.assertTrue(message is not None)
        self.assertTrue(tag in message.text)
        # Test /done
        await user.send_message('/done')
        message = await user.get_message()
        self.assertTrue(message is not None)
        self.assertTrue(tag in message.text)
        # Test /done again
        await user.send_message('/done')
        message = await user.get_message()
        self.assertTrue(message is not None)
        self.assertTrue(tag not in message.text)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
