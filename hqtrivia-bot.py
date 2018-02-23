#!/usr/bin/python
import sys
import json
import websocket
import grequests
import requests
import utils

USER_ID = '***REMOVED***'
BEARER_TOKEN = '***REMOVED***'
HEADERS = {
    'User-Agent'    : 'hq-viewer/1.2.4 (iPhone; iOS 11.1.1; Scale/3.00)',
    'Authorization' : 'Bearer %s' % BEARER_TOKEN,
    'x-hq-stk'      : 'Mg==',
    'x-hq-client'   : 'Android/1.2.0',
}
broadcastEnded = False

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


# Message handler
def on_message(ws, message):    

     # Decode JSON data
    data_start = message.find('{')
    if data_start >= 0:
        data = json.loads(message[data_start:])

        # Get message types
        if data.get('type') != 'interaction':
            print('MESSAGE: %s' % message)
        if data.get('type') == 'broadcastEnded' and not data.get('reason'):
            broadcastEnded = True
            print('Broadcast ended.')
            ws.close()
        if data.get('type') == 'question':
            if data.get('answers') and data.get('type') == 'question':
                utils.predict_answers(data.get('question'), utils.build_answers(data.get('answers')))

def on_error(ws, error):
    print('ERROR: %s' % error)

def on_ping(ws, data):
    print('RECEIVED PING: %s, SENDING PONG' % data)
    ws.pong(data)

def on_close(ws):
    print('SOCKET CLOSED')

if __name__ == "__main__":

    if not "test" in sys.argv:
        socket_url = get_socket_url()
        if socket_url:
            print('CONNECTING TO %s' % socket_url)
            websocket.enableTrace(True)
            ws = websocket.WebSocketApp(socket_url,
                on_message = on_message,
                on_error = on_error,
                on_close = on_close,
                header = HEADERS
            )
            while not broadcastEnded:
                try:
                    ws.run_forever()
                except:
                    print('RECONNECTING')
    else:
        print("Running in Test Mode")

        # Load questions from file
        questions = json.load(open('questions.json'))

        # Loop through questions
        total = 0
        total_correct = 0
        for q in questions:
        #question = questions[0]
            prediction = utils.predict_answers(q.get('question'), q.get('answers'))
            prediction_correct = prediction == q.get('correct')
            print('Predicted: %s, Correct: %s' % (prediction, q.get('correct')))
            print('Correct? %s' % ('Yes' if prediction_correct else 'No'))
            total += 1
            total_correct += 1 if prediction_correct else 0
            if total == 20:
                break;

        print("Testing Complete")
        print("Total Correct: %s/%s" % (total_correct, total))
