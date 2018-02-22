#!/usr/bin/python
import time
import json
import websocket
import requests
import urllib.parse
try:
    import thread
except ImportError:
    import _thread as thread

USER_ID = '***REMOVED***'
BEARER_TOKEN = '***REMOVED***'
HEADERS = {
    'User-Agent'    : 'hq-viewer/1.2.4 (iPhone; iOS 11.1.1; Scale/3.00)',
    'Authorization' : 'Bearer %s' % BEARER_TOKEN,
    'x-hq-client'   : 'iOS/1.2.4 b59',
}

# Get broadcast socket URL
def get_socket_url():
    resp = requests.get('https://api-quiz.hype.space/shows/now?type=hq&userId=%s' % USER_ID, headers=HEADERS)
    json = resp.json()

    # Get next show time and prize
    nextShowTime = json.get('nextShowTime')
    nextShowPrize = json.get('nextShowPrize')

    # Check if broadcast socket URL exists
    if  not json.get('broadcast') or not json.get('broadcast').get('socketUrl'):
        print('Broadcast ended. Next show on %s for %s.' % (nextShowTime, nextShowPrize))
        return None

    # Return socket URL for websocket connection
    return json.get('broadcast').get('socketUrl').replace('https', 'wss')


# Build set of answers from raw data
def build_answers(raw_answers):
    answers = {
        'A': raw_answers[1]['text'],
        'B': raw_answers[2]['text'],
        'C': raw_answers[3]['text']
    }
    return answers


# Build query set from data and options
def build_queries(question, answers, includeAnswers=False, change=False):
    queries = [question]

    if 'Which of these' in question and change is True:
        question = question.replace('Which of these', 'what')
        question = implode(' ', array_map('singularize', (array)str_word_count(question, 1)))
        print(question)

    if includeAnswers is True:
        if change is False:
            queries.append('%s "%s"' % (question, '"  "'.join(answers)))

        for answer in answers:
            queries.append('%s "%s"' % (question, answer))

    return map(lambda v: grequests.get('https://www.google.ca/search?q=%s' % urllib.parse.urlencode(v)), queries)
        + map(lambda v: grequests.get('https://ca.search.yahoo.com/search?ei=UTF-8&nojs=1&p=%s' % urllib.parse.urlencode(v)), queries)


# Get answer predictions
def predict_answers(answers, question):
    print('--------------------------------------')
    print(question)

    # Check for NOT in question
    if ' not ' in question:
        print('--------------------------------------------------------')
        print('"NOT" DETECTED. USE THE ANSWER THAT IS THE LEAST SUCCESSFUL')
        print('--------------------------------------------------------')

    # Use method 1
    print ('METHOD 1')
    queries = build_queries(
        question,
        answers
    )
    responses = grequests.map(queries)
    handle_responses(responses, answers, question)

    # Use method 2
    print ('METHOD 2')
    queries = build_queries(
        question,
        answers,
        True
    )
    responses = grequests.map(queries)
    handle_responses(responses, answers, question)

    # Use method 3 (optional)
    if 'Which of these' in question:
        print ('Special METHOD 3')
        queries = build_queries(
            question,
            answers,
            False,
            True
        )
        handle_responses(responses, answers, question)


# Message handler
def on_message(ws, message):
    print('MESSAGE: %s' % message)

    # Find start of JSON data
    data_start = message.find('{')
    if data_start >= 0:

        # Decode JSON data
        data = json.loads(message[data_start:])
        if data.get('type') == 'broadcastEnded' and not data.get('reason'):
            ws.close()
            print('Broadcast ended.')
        elif data.get('type') == 'question':
            if data.get('answers') and data.get('type') == 'question':
                predict_answers(build_answers(data.get('answers')), data.get('question'))


# Error handler
def on_error(ws, error):
    print('ERROR: %s' % error)


# Socket close handler
def on_close(ws):
    print('SOCKET CLOSED')


if __name__ == "__main__":
    socket_url = get_socket_url()

    if socket_url:
        websocket.enableTrace(True)
        ws = websocket.WebSocketApp("ws://socket_url",
            on_message = on_message,
            on_error = on_error,
            on_close = on_close
        )
        ws.run_forever()
