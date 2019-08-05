# Face Recognition Telegram Bot
This bot uses the following for face recognition
- `https://github.com/ageitgey/face_recognition`

face_recognition uses dlib's default model 
- `https://github.com/ageitgey/face_recognition_models/`

It is possible to train a new model with more asian faces for better accuracy 
- `http://dlib.net/dnn_metric_learning_on_images_ex.cpp.html`
- `https://github.com/deepinsight/insightface/wiki/Dataset-Zoo`
- `https://drive.google.com/drive/folders/1ADcZugpo8Z6o5q1p2tIAibwhsL8DcVwH`
- `https://github.com/deepinsight/insightface/issues/256`

The dlib model extracts face encoding that can later be used for calculating face distance. The current implementation uses KNN and SVM to classify encoding with its label.

## Prepare pre-commit hook
```
# Run this if you are developing this bot
chmod +x prepare.sh
./prepare.sh
```

## Credentials
The following credentials are required to deploy this bot. Please read `https://core.telegram.org/bots#6-botfather` for instruction to generate bot token. <br/>
*** Use `/setprivacy` to disable privacy, if bot is used in group ***
- Development bot token `./dev_token.txt`
    - `123456789:ABCDEFG`
- Development root user token `./dev_root_token.txt`
    - `@abc1234user`
- Production bot token `./prod_token.txt`
    - `123456789:ABCDEFG`
- Production root user token `./prod_root_token.txt`
    - `@abc1234user`

The following credentials are required to run test cases on this bot. Please read `https://core.telegram.org/api/obtaining_api_id` for instruction to generate API credentials.
- Telegram account session `./test/user.session`
- User credentials `./test/user_token.txt`
    - API ID
    - API HASH
    - BOT's id 
    - USER's id <br/>
        - Example:
            - 123456
            - a1234567
            - @face_recognition_1234_bot
            - @user123456
Use the script `create_session.py` with the above API credentials to generate the session file.

## Docker instructions
It's most ideal to use docker for managing this bot. <br/>
Please remember to re-build the container after any changes.
```
# Build container for development
docker-compose build
# Run bot for development
docker-compose run recog
# Run bot (detached) for development
docker-compose up
# Stop bot for development
docker-compose down
# Read logs
docker-compose logs recog

# Build container for production
docker-compose -f docker-compose-prod.yml build
# Run bot for production
docker-compose -f docker-compose-prod.yml run recog
# Run bot (detached) for production
docker-compose -f docker-compose-prod.yml up
# Stop bot for production
docker-compose -f docker-compose-prod.yml down
# Read logs
docker-compose -f docker-compose-prod.yml logs recog

# Build container for testing
docker-compose -f docker-compose-test.yml build
# Run bot for testing
docker-compose -f docker-compose-test.yml run recog
```
