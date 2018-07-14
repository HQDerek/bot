# hqtrivia-bot

### Install Bot
 * Install Pipenv `sudo pip install pipenv`
 * Install NLTK corpora `python3 -m nltk.downloader stopwords`
 * Create Pipenv virtual environment `pipenv --three install --dev`


### Run HQ Trivia Bot
 * Run bot `pipenv run bot`


### Add a Round to Cache
 * Run cache refresh `pipenv run cache refresh`
 * Run cache prune `pipenv run cache prune`
 * Run cache export `pipenv run cache export`


### Replay HQ Trivia Round
 * The bot can be tested by replaying a set of questions from saved games.
 * Run `pipenv run replay <game-id>[,<game-id>]` to test specific games in the `games` directory.


### Run Pytest Unit Tests
 * Run pytest `pipenv run test`


### Run Pylint PEP8 Linting
 * Run pylint `pipenv run lint`


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
