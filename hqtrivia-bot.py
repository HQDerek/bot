#!/usr/bin/python
import time
import json
import websocket
import requests
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
