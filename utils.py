""" utilities for the HQ Trivia bot project """
import re
import sys
import webbrowser
import urllib.parse
from enum import Enum
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from requests_cache import CachedSession
from requests_futures.sessions import FuturesSession


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


class Weights(Enum):
    """ weights for each algorithm """
    GOOGLE_SUMMARY_ANSWER_COUNT = 200
    GOOGLE_RESULTS_NUMBER = 100


def build_answers(raw_answers):
    """" Build set of answers from raw data """
    answers = {
        'A': raw_answers[0]['text'],
        'B': raw_answers[1]['text'],
        'C': raw_answers[2]['text']
    }
    return answers


def answer_words_queries(question, _answers):
    """" Build google query set from data and options """
    queries = [question]
    return ['https://www.google.co.uk/search?pws=0&q=' \
        + urllib.parse.quote_plus(question) for q in queries]


def count_results_queries(question, answers):
    """" Build google query set from data and options """
    queries = ['%s "%s"' % (question, answer) for answer in answers.values()]
    return ['https://www.google.co.uk/search?pws=0&q=' \
        + urllib.parse.quote_plus(q) for q in queries]


def predict_answers(data, answers):
    """ Get answer predictions """
    confidence = {
        'A': 0,
        'B': 0,
        'C': 0
    }
    question = data.get('question')

    if not data.get('is_replay', False):
        webbrowser.open("http://google.com/search?q="+question)

    print('\n\n\n\n\n')
    print('------------ %s %s | %s ------------' % ('QUESTION', data.get('questionNumber'), data.get('category')))
    print(Colours.BOLD.value + question + Colours.ENDC.value)
    print('------------ %s ------------' % 'ANSWERS')
    print(answers)
    print('------------------------')
    print('\n')

    if not data.get('is_replay', False):
        session = FuturesSession()
    else:
        session = CachedSession('db/cache', allowable_codes=(200, 302, 304))

    answer_words_resp = [
        (resp.result() if hasattr(resp, 'result') else resp) \
        for resp in map(session.get, answer_words_queries(question, answers))
    ]
    count_results_resp = [
        (resp.result() if hasattr(resp, 'result') else resp) \
        for resp in map(session.get, count_results_queries(question, answers))
    ]

    confidence = find_answer_words_google(question, answers, confidence, answer_words_resp)
    confidence = count_results_number_google(question, answers, confidence, count_results_resp)

    # Calculate prediction
    if 'NOT' in question or 'NEVER' in question:
        prediction = min(confidence, key=confidence.get)
    else:
        prediction = max(confidence, key=confidence.get)
    total_occurrences = sum(confidence.values())
    for index, count in confidence.items():
        likelihood = int(count/total_occurrences * 100) if total_occurrences else 0
        confidence[index] = '%d%%' % likelihood
        result = 'Answer %s: %s - %s%%' % (index, answers[index], likelihood)
        print(Colours.BOLD.value + result + Colours.ENDC.value if index == prediction else result)

    print('\n')
    return prediction if confidence[prediction] else None, confidence


def find_answer_words_google(_question, answers, confidence, responses):
    """ METHOD 1: Find answer in Google search result descriptions """
    occurrences = {'A': 0, 'B': 0, 'C': 0}
    response = responses[0]

    soup = BeautifulSoup(response.text, "html5lib")

    # Check for rate limiting page
    if '/sorry/index?continue=' in response.url:
        sys.exit('ERROR: Google rate limiting detected.')

    results = ''
    # Get search descriptions
    for element in soup.find_all(class_='st'):
        results += " " + element.text
    # Get search titles
    for element in soup.find_all(class_='r'):
        results += " " + element.text
    # Get search result card
    for element in soup.find_all(class_='mod'):
        results += " " + element.text
    # Get related search results card
    for element in soup.find_all(class_='brs_col'):
        results += " " + element.text
    results_words = get_raw_words(results)

    # Find answer words in search descriptions
    for index, answer in answers.items():
        answer_words = get_raw_words(answer)
        occurrences[index] += results_words.count(answer_words)

    print("\nMETHOD 1")
    print("Count: %s%s%s" % (Colours.BOLD.value, occurrences, Colours.ENDC.value))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for index, count in occurrences.items():
        if total_occurrences:
            confidence[index] += int(count / total_occurrences * Weights.GOOGLE_SUMMARY_ANSWER_COUNT.value)

    return confidence


def count_results_number_google(_question, _answers, confidence, responses):
    """ METHOD 2: Compare number of results found by Google """
    occurrences = {'A': 0, 'B': 0, 'C': 0}

    # Loop through search results
    for index, response in enumerate(responses):
        soup = BeautifulSoup(response.text, "html5lib")
        if soup.find(id='resultStats'):
            results_count_text = soup.find(id='resultStats').text.replace(',', '')
            results_count = re.findall(r'\d+', results_count_text)
            if results_count:
                occurrences[chr(65 + index)] += int(results_count[0])

    print("\nMETHOD 2")
    print("Search Results: %s%s%s\n" % (Colours.BOLD.value, occurrences, Colours.ENDC.value))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for index, count in occurrences.items():
        if total_occurrences:
            confidence[index] += int(count / total_occurrences * Weights.GOOGLE_RESULTS_NUMBER.value)

    return confidence


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
