# pylint: disable=duplicate-code, too-many-statements
''' Unit test for user model integration '''
import unittest
import logging

from test.common import async_test, UserModelTestCase
from PIL import Image
from utils import image_to_file

# Initialize loggers
logging.basicConfig(level=logging.WARNING)


class TestTrainPredict(UserModelTestCase):
    ''' Test user model '''

    @async_test
    async def test_no_permission(self):
        ''' Test with no permission '''
        self.database.drop_testing_database()  # Clear database
        user = self.user
        for cmd in ['help', 'start', 'user', 'admin', 'train', 'done',
                    'addadmin', 'adduser']:
            await user.send_message('/{}'.format(cmd))
            message = await user.get_message()
            self.assertEqual(message, None)
        # Send photo with no face
        no_face_image = Image.new('RGB', (30, 30), color='white')
        no_face_photo = image_to_file(no_face_image)
        await user.send_photo(no_face_photo)
        message = await user.get_message(10)
        self.assertEqual(message, None)

    @async_test
    async def test_user_permission(self):
        ''' Test with user permission '''
        # Setup permission
        self.database.drop_testing_database()  # Clear database
        if '@' not in self.user.user_id:
            self.user.user_id = '@' + self.user.user_id
        self.database.add_user(self.user.user_id, 'user')
        # Test forbidden commands
        user = self.user
        for cmd in ['user', 'admin', 'train', 'done', 'addadmin', 'adduser']:
            await user.send_message('/{}'.format(cmd))
            message = await user.get_message()
            self.assertTrue('Permission denied' in message.text)
        # Send photo with no face
        no_face_image = Image.new('RGB', (30, 30), color='white')
        no_face_photo = image_to_file(no_face_image)
        await user.send_photo(no_face_photo)
        message = await user.get_message(10)
        self.assertTrue('No model' in message.text
                        or 'No face found' in message.text)

    @async_test
    async def test_admin_permission(self):
        ''' Test with admin permission '''
        # Setup permission
        self.database.drop_testing_database()  # Clear database
        if '@' not in self.user.user_id:
            self.user.user_id = '@' + self.user.user_id
        self.database.add_user(self.user.user_id, 'admin')

        # Test forbidden commands
        user = self.user
        for cmd in ['admin', 'addadmin']:
            await user.send_message('/{}'.format(cmd))
            message = await user.get_message()
            self.assertTrue('Permission denied' in message.text)

        # Run predict
        no_face_image = Image.new('RGB', (30, 30), color='white')
        no_face_photo = image_to_file(no_face_image)
        await user.send_photo(no_face_photo)
        message = await user.get_message(10)
        self.assertTrue('No model' in message.text
                        or 'No face found' in message.text)

        # Run /train with label
        tag = 'testlabel1'
        await user.send_message('/train {}'.format(tag))
        message = await user.get_message()
        self.assertTrue(tag in message.text)
        # Send photo with one face
        one_face_photo = open('./test/media/wong_1.jpg', 'rb')
        await user.send_photo(one_face_photo)
        one_face_photo.close()
        # Check message
        message = await user.get_message()
        self.assertTrue(tag in message.text)
        self.assertTrue('more' in message.text)
        await user.send_message('/done')
        message = await user.get_message()
        self.assertTrue('Done' in message.text)
        self.assertTrue(tag in message.text)

        # List users
        await user.send_message('/user')
        message = await user.get_message()
        self.assertTrue('List of users' in message.text)

        # Add user
        if '@' not in self.user.bot_id:
            self.user.bot_id = '@' + self.user.bot_id
        await user.send_message('/adduser {}'.format(self.user.bot_id))
        message = await user.get_message()
        self.assertTrue('Added user' in message.text)
        self.assertTrue(self.user.bot_id in message.text)

        # Cancel on removing user
        await user.send_message('/user')
        message = await user.get_message()
        self.assertTrue('List of users' in message.text)
        self.assertEqual(message.button_count, 1)
        self.assertTrue(self.user.bot_id in message.buttons[0][0].text)
        # Click on user
        await message.click(0)
        # Display Remove and cancel button
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 2)
        await message.click(1)  # Cancel
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 1)
        self.assertTrue(self.user.bot_id in message.buttons[0][0].text)

        # Remove user
        await user.send_message('/user')
        message = await user.get_message()
        self.assertTrue('List of users' in message.text)
        self.assertEqual(message.button_count, 1)
        self.assertTrue(self.user.bot_id in message.buttons[0][0].text)
        # Click on user
        await message.click(0)
        # Display Remove and cancel button
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 2)
        await message.click(0)  # Remove
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 0)

    @async_test
    async def test_root_admin_permission(self):
        ''' Test with root_admin permission '''
        # Setup permission
        self.database.drop_testing_database()  # Clear database
        if '@' not in self.user.user_id:
            self.user.user_id = '@' + self.user.user_id
        self.database.add_user(self.user.user_id, 'root_admin')
        user = self.user

        # Run predict
        no_face_image = Image.new('RGB', (30, 30), color='white')
        no_face_photo = image_to_file(no_face_image)
        await user.send_photo(no_face_photo)
        message = await user.get_message(10)
        self.assertTrue('No model' in message.text
                        or 'No face found' in message.text)

        # Run /train with label
        tag = 'testlabel1'
        await user.send_message('/train {}'.format(tag))
        message = await user.get_message()
        self.assertTrue(tag in message.text)
        # Send photo with one face
        one_face_photo = open('./test/media/wong_1.jpg', 'rb')
        await user.send_photo(one_face_photo)
        one_face_photo.close()
        # Check message
        message = await user.get_message()
        self.assertTrue(tag in message.text)
        self.assertTrue('more' in message.text)
        await user.send_message('/done')
        message = await user.get_message()
        self.assertTrue('Done' in message.text)
        self.assertTrue(tag in message.text)

        # List users
        await user.send_message('/user')
        message = await user.get_message()
        self.assertTrue('List of users' in message.text)

        # Add user
        if '@' not in self.user.bot_id:
            self.user.bot_id = '@' + self.user.bot_id
        await user.send_message('/adduser {}'.format(self.user.bot_id))
        message = await user.get_message()
        self.assertTrue('Added user' in message.text)
        self.assertTrue(self.user.bot_id in message.text)

        # Cancel on removing user
        await user.send_message('/user')
        message = await user.get_message()
        self.assertTrue('List of users' in message.text)
        self.assertEqual(message.button_count, 1)
        self.assertTrue(self.user.bot_id in message.buttons[0][0].text)
        # Click on user
        await message.click(0)
        # Display Remove and cancel button
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 2)
        await message.click(1)  # Cancel
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 1)
        self.assertTrue(self.user.bot_id in message.buttons[0][0].text)

        # Remove user
        await user.send_message('/user')
        message = await user.get_message()
        self.assertTrue('List of users' in message.text)
        self.assertEqual(message.button_count, 1)
        self.assertTrue(self.user.bot_id in message.buttons[0][0].text)
        # Click on user
        await message.click(0)
        # Display Remove and cancel button
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 2)
        await message.click(0)  # Remove
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 0)

        # List admins
        await user.send_message('/admin')
        message = await user.get_message()
        self.assertTrue('List of admins' in message.text)

        # Add admin
        if '@' not in self.user.bot_id:
            self.user.bot_id = '@' + self.user.bot_id
        await user.send_message('/addadmin {}'.format(self.user.bot_id))
        message = await user.get_message()
        self.assertTrue('Added admin' in message.text)
        self.assertTrue(self.user.bot_id in message.text)

        # Cancel on removing admin
        await user.send_message('/admin')
        message = await user.get_message()
        self.assertTrue('List of admins' in message.text)
        self.assertEqual(message.button_count, 1)
        self.assertTrue(self.user.bot_id in message.buttons[0][0].text)
        # Click on admin
        await message.click(0)
        # Display Remove and cancel button
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 2)
        await message.click(1)  # Cancel
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 1)
        self.assertTrue(self.user.bot_id in message.buttons[0][0].text)

        # Remove admin
        await user.send_message('/admin')
        message = await user.get_message()
        self.assertTrue('List of admins' in message.text)
        self.assertEqual(message.button_count, 1)
        self.assertTrue(self.user.bot_id in message.buttons[0][0].text)
        # Click on admin
        await message.click(0)
        # Display Remove and cancel button
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 2)
        await message.click(0)  # Remove
        message = await user.get_message(last=True)
        self.assertEqual(message.button_count, 0)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
