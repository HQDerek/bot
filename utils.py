""" Utilities for the HQ Trivia bot project """
import re
from enum import Enum
from nltk.corpus import stopwords
<<<<<<< HEAD
from requests_cache import CachedSession
from requests_futures.sessions import FuturesSession
=======
>>>>>>> @{-1}


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


def get_significant_words(question_words):
    """ Returns a list of the words from the input string that are not in NLTK's stopwords """
    our_stopwords = set(stopwords.words('english'))
    return list(filter(lambda word: word not in our_stopwords, question_words.split(' ')))


def get_raw_words(data):
    """ Extract raw words from data """
    data = re.sub(r'[^\w ]', '', data).replace(' and ', ' ').strip()
    words = data.replace('  ', ' ').lower()
    return words
