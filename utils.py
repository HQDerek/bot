""" Utilities for the HQ Trivia bot project """
import re
from enum import Enum
from glob import glob
from configparser import ConfigParser
from json import JSONDecodeError
from requests import post, get
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

WORDNET = WordNetLemmatizer()

class Colours(Enum):
    """ console colours """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def find_keywords(keywords, data):
    """ Find keywords in specified data """
    words_found = []
    for keyword in keywords:
        if len(keyword) > 2:
            if keyword in data and keyword not in words_found:
                words_found.append(data.count(keyword))
    return words_found


def make_it_rain(headers):
    """ Make it rain """
    resp = post('https://api-quiz.hype.space/easter-eggs/%s' % 'makeItRain', headers=headers)
    try:
        print('Make it rain: %s' % resp.json())
    except ValueError:
        pass


def make_it_rain_for_all(headers):
    """ make it rain for me and then others"""
    try:
        for filename in sorted(glob('config*.ini')):
            config = ConfigParser()
            config.read(filename)
            other_headers = headers.copy()
            other_headers.update({'Authorization': 'Bearer %s' % config.get('Auth', 'bearer_token')})
            print("Making it rain for %s:" % (filename.split('-')[1] if len(filename.split('-')) > 1 else 'me'))
            make_it_rain(other_headers)
    except TypeError:
        pass


def get_significant_words(question_words):
    """ Returns a list of the words from the input string that are not in NLTK's stopwords """
    our_stopwords = set(stopwords.words('english'))
    return list(filter(lambda word: word not in our_stopwords, question_words.split(' ')))




def get_raw_words(data):
    """ Extract raw words from data """
    data = re.sub(r'[^\w ]', '', data).lower().replace(' and ', ' ')
    words_list = data.replace('  ', ' ').strip().split(' ')
    words = ' '.join([WORDNET.lemmatize(word) for word in words_list])
    return words


def generate_token(headers, number):
    """ Generate an auth token for number """
    unauth_headers = headers.copy()
    unauth_headers.pop('Authorization', None)
    phone_resp = post('https://api-quiz.hype.space/verifications', headers=unauth_headers, data={
        'method': 'sms',
        'phone': number
    }).json()
    verification_id = phone_resp.get('verificationId')
    if not verification_id:
        print('Something went wrong. %s' % phone_resp.get('error', ''))
    else:
        print('Verification sent to %s.' % number)
        code = input("Please enter the code: ")
        code_resp = post('https://api-quiz.hype.space/verifications/%s' % verification_id,
                         headers=unauth_headers, data={'code': code}).json()
        if not code_resp.get('auth'):
            print('Something went wrong. %s' % code_resp.get('error', ''))
        else:
            verify_file = 'config-%s-%s.ini' % (code_resp.get('auth').get('username'), code)
            with open(verify_file, 'w') as out:
                out.write('%s\n%s\n%s' % (
                    '[Auth]',
                    'user_id = %s' % code_resp.get('auth').get('userId'),
                    'bearer_token = %s' % code_resp.get('auth').get('accessToken')
                ))
            print('Verification successful. Details stored in %s' % verify_file)


def get_stats(headers, username):
    """ Query play stats for a given user """
    resp = get(f'https://api-quiz.hype.space/users?q={username}', headers=headers)
    try:
        json = resp.json()
        user_id = None
        users = json.get('data', [])
        if users is not None:
            for user in users:
                if user.get('username') == username:
                    user_id = user.get('userId')
                    user = get('https://api-quiz.hype.space/users/{}'.format(user_id), headers=headers).json()
                    print('User:\t\t{}'.format(user.get('username')))
                    print('Total Earnings:\t{}'.format(user.get('leaderboard').get('total')))
                    print('Games Played:\t{}'.format(user.get('gamesPlayed')))
                    print('Wins:\t\t{}'.format(user.get('winCount')))
            if not user_id:
                print('%s is not a user.' % username)
        else:
            print('%s is not a user.' % username)
    except JSONDecodeError:
        pass
