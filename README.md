# hqtrivia-bot

### Run HQ Trivia Bot
`python hqtrivia-bot.py`

### Get Bearer Token and User ID
 * Install [Packet Capture](https://play.google.com/store/apps/details?id=app.greyshirts.sslcapture) for Android
 * Sniff packets for HQ Trivia and look for requests to `api-quiz.hype.space`.
 * Find the request with `Authorization: Bearer` and look for `"userId": 123` response.