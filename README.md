# hqtrivia-bot

### Install Bot
 * Install virtualenv `pip install virtualenv`
 * Create virtual environment `virtualenv hqtrivia-bot`
 * Start virtual environment `source hqtrivia-bot/bin/activate`
 * Install bot dependencies `pip install -r requirements.txt`
 * Install NLTK corpora `python -m nltk.downloader punkt; python -m nltk.downloader averaged_perceptron_tagger`


### Get Bearer Token and User ID
 * Install [Packet Capture](https://play.google.com/store/apps/details?id=app.greyshirts.sslcapture) for Android
 * Sniff packets for HQ Trivia and look for requests to `api-quiz.hype.space`.
 * Find the request with `Authorization: Bearer` in the header and `"userId": 123` in the response.
 * Set these as environment variables with `export HQTRIVIA_USER_ID=123` and `export HQTRIVIA_BEARER_TOKEN=abc`.


### Run HQ Trivia Bot
 * Ensure virtualenv is activated `source hqtrivia-bot/bin/activate`
 * Run bot `python hqtrivia-bot.py`


### Test HQ Trivia Bot
 * The bot can be tested by running against a set of saved questions and answers.
 * Run `python hqtrivia-bot.py test <N>` to test questions from round numbers 1 to <N>
