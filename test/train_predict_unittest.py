# pylint: disable=duplicate-code, too-many-statements
''' Unit test for train and predict commands '''
import unittest
import logging

from test.common import async_test, BaseTestCase
from PIL import Image
from utils import image_to_file

# Initialize loggers
logging.basicConfig(level=logging.WARNING)


class TestTrainPredict(BaseTestCase):
    ''' Test train and predict commands '''

    @async_test
    async def test_train_incorrect_num_face(self):
        ''' Test train with incorrect number of face '''
        user = self.user
        tag = 'test_label_1'
        # Run /train <tag>
        await user.send_message('/train {}'.format(tag))
        message = await user.get_message()
        self.assertTrue(tag in message.text)
        # Send photo with no face
        no_face_image = Image.new('RGB', (30, 30), color='white')
        no_face_photo = image_to_file(no_face_image)
        await user.send_photo(no_face_photo)
        message = await user.get_message(10)
        self.assertEqual('No face found', message.text)
        # Send photo with two faces
        two_face_photo = open('./test/media/two_wong.png', 'rb')
        await user.send_photo(two_face_photo)
        two_face_photo.close()
        message = await user.get_message(10)
        self.assertEqual('More than one face found', message.text)
        # Done
        await user.send_message('/done')
        message = await user.get_message()
        self.assertTrue(tag in message.text)

    @async_test
    async def test_no_model_predict(self):
        ''' Test predict with no model '''
        user = self.user
        # Send photo with one face
        one_face_photo = open('./test/media/wong_1.jpg', 'rb')
        await user.send_photo(one_face_photo)
        one_face_photo.close()
        message = await user.get_message(10)
        self.assertTrue('No model' in message.text)

    @async_test
    async def test_train_predict(self):
        ''' Test train and predict '''
        user = self.user
        tag = 'test_wong_label_1'
        # Run /train <tag>
        await user.send_message('/train {}'.format(tag))
        message = await user.get_message()
        self.assertTrue(tag in message.text)
        # Send photo with one face
        one_face_photo = open('./test/media/wong_1.jpg', 'rb')
        await user.send_photo(one_face_photo)
        one_face_photo.close()
        message = await user.get_message(10)
        self.assertTrue('Model trained' in message.text)
        self.assertTrue(tag in message.text)
        # Done
        await user.send_message('/done')
        message = await user.get_message()
        self.assertTrue(tag in message.text)

        # Trigger re-train model update
        tag = 'test_ma_label_1'
        await user.send_message('/train {}'.format(tag))
        message = await user.get_message()
        self.assertTrue(tag in message.text)
        # Send photo with one face
        one_face_photo = open('./test/media/ma_1.jpg', 'rb')
        await user.send_photo(one_face_photo)
        one_face_photo.close()
        message = await user.get_message(10)
        self.assertTrue('Model trained' in message.text)
        self.assertTrue(tag in message.text)
        # Done
        await user.send_message('/done')
        message = await user.get_message()
        self.assertTrue(tag in message.text)

        # Test predict with faces
        # Send photo with original face
        tag = 'test_wong_label_1'
        one_face_photo = open('./test/media/wong_1.jpg', 'rb')
        await user.send_photo(one_face_photo)
        one_face_photo.close()
        messages = await user.get_messages(num=3, retry=20)
        for i in range(3):
            self.assertIn(tag, messages[i].text)
        self.assertIn('ref', messages[2].text)
        # Send photo with face of same person
        one_face_photo = open('./test/media/wong_2.jpg', 'rb')
        await user.send_photo(one_face_photo)
        one_face_photo.close()
        messages = await user.get_messages(num=3, retry=20)
        for i in range(3):
            self.assertIn(tag, messages[i].text)
        self.assertIn('ref', messages[2].text)
        # Send photo with two faces of same person
        two_face_photo = open('./test/media/two_wong.png', 'rb')
        await user.send_photo(two_face_photo)
        two_face_photo.close()
        messages = await user.get_messages(num=3, retry=20)
        parts = messages[0].text.split('\n')
        self.assertIn(tag, parts[0])
        self.assertIn(tag, parts[1])
        self.assertIn(tag, messages[1].text)
        self.assertIn(tag, messages[2].text)
        self.assertIn('ref', messages[2].text)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
