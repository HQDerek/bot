# hqtrivia-bot

### Install Bot
 * Install Pipenv `sudo pip install pipenv`
 * Create Pipenv virtual environment `pipenv --three install`
 * Activate virtual environment `pipenv shell`
 * Install NLTK corpora `python3 -m nltk.downloader stopwords`


### Get Bearer Token and User ID
 * Install [Packet Capture](https://play.google.com/store/apps/details?id=app.greyshirts.sslcapture) for Android
 * Sniff packets for HQ Trivia and look for requests to `api-quiz.hype.space`, namely the endpoint `GET /users/me`.
 * Find the request with `Authorization: Bearer` in the header and `"userId"` in the response.


### Add configuration file
 * Create a file with the `userId` and `Bearer` values using the format below and save as `config.ini`.

```
[Auth]
user_id = <userId>
bearer_token = <Bearer>
```


### Run HQ Trivia Bot
 * Ensure pipenv is activated `pipenv shell`
 * Run bot `python3 hqtrivia-bot.py`


### Test HQ Trivia Bot
 * The bot can be tested by running against a set of questions from saved games.
 * Run `python hqtrivia-bot.py test <game-id>[,<game-id>]` to test specific games in the `games` directory.
