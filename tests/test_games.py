""" unit tests for the hqtrivia_bot.py """
from glob import glob
from json import load
from mock import Mock, patch
from requests_cache import CachedSession

def cached_get(url):
    """ cached session """
    session = CachedSession('query_cache', allowable_codes=(200, 302, 304))
    response = Mock()
    response.result.return_value = session.get(url)
    return response

@patch('utils.FuturesSession.get', side_effect=cached_get)
def test_games():
    """ testing games """

    for filename in glob('games/*.json'):
        game = load(open(filename))
        for turn in game.get('questions'):
            turn['is_replay'] = True
            #(prediction, confidence) = utils.predict_answers(turn, turn.get('answers'))
