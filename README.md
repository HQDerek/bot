# hqtrivia-bot

### Install Bot
 * Install virtualenv `pip install virtualenv`
 * Create virtual environment `virtualenv hqtrivia-bot`
 * Start virtual environment `source hqtrivia-bot/bin/activate`
 * Install bot dependencies `pip install -r requirements.txt`
 * Install NLTK corpora `python -m nltk.downloader punkt; python -m nltk.downloader averaged_perceptron_tagger`


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
 * Ensure virtualenv is activated `source hqtrivia-bot/bin/activate`
 * Run bot `python hqtrivia_bot.py`

##### Arguments

|Argument|Function|
|---|---|
|`--browser`|Open browser with question search|


### Test HQ Trivia Bot
 * The bot can be tested by running against a set of questions from saved games.
 * Run `python hqtrivia_bot.py test <game-id>[,<game-id>]` to test specific games in the `games` directory.
