# hqtrivia-bot

Welcome to HQ Trivia Bot! Thanks for contributing. Here are the steps to get started.


### Install Bot
 * Ensure you have Python 3 installed on your system.
 * Install Pipenv `sudo pip install pipenv`
 * Create Pipenv virtual environment `pipenv --three install --dev`
 * Install NLTK corpora `pipenv run python3 -m nltk.downloader stopwords`


### Run HQ Trivia Bot
To play a live game of HQ Trivia, you first need to generate a login token.
 * Generate token with `pipenv run generate-token <phone-number>`
Ensure that this file is named `config.ini`, then you can connect to a live game.
 * Run bot `pipenv run bot`


### Import Cached Games
Before running tests or cache operations, ensure the local database has been imported.
 * Run cache import `pipenv run cache import`


### Add Game to Cache
After playing a live game, import the game to the local database and export the cached responses.
 * Run cache refresh `pipenv run cache refresh`
 * Run cache prune `pipenv run cache prune`
 * Run cache export `pipenv run cache export`


### Replay HQ Trivia Round
The bot can be tested by replaying a set of questions from saved games.
 * Run `pipenv run replay <game-id>[,<game-id>]` to test specific games in the `games` directory.


### Run Pytest Unit Tests
 * Run pytest `pipenv run test`


### Run Pylint PEP8 Linting
 * Run pylint `pipenv run lint`

