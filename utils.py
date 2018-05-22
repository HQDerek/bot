import re
import sys
import nltk
import requests_cache
import grequests
import urllib.parse
import os
import json
import glob
import webbrowser
from time import sleep
from bs4 import BeautifulSoup

class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class weights:
    GOOGLE_SUMMARY_ANSWER_COUNT = 200
    NUM_GOOGLE_RESULTS = 100
    WIKIPEDIA_PAGE_QUESTION_COUNT = 100

# Build set of answers from raw data
def build_answers(raw_answers):
    answers = {
        'A': raw_answers[0]['text'],
        'B': raw_answers[1]['text'],
        'C': raw_answers[2]['text']
    }
    return answers


# Build google query set from data and options
def build_google_queries(question, answers, session):
    queries = [question]
    queries += ['%s "%s"' % (question, answer) for answer in answers.values()]

    return [grequests.get('https://www.google.co.uk/search?q=' + urllib.parse.quote_plus(q), session=session) for q in queries]


# Build wikipedia query set from data and options
def build_wikipedia_queries(question, answers, session):
    queries = list(answers.values())

    return [grequests.get('https://en.wikipedia.org/wiki/Special:Search?search=' + urllib.parse.quote_plus(q), session=session) for q in queries]


# Get answer predictions
def predict_answers(data, answers):

    confidence = {
        'A': 0,
        'B': 0,
        'C': 0
    }
    question = data.get('question')

    if not data.get('is_testing', False):
        webbrowser.open("http://google.com/search?q="+question)

    print('------------ %s %s | %s ------------' % ('QUESTION', data.get('questionNumber'), data.get('category')))
    print(colors.BOLD + question + colors.ENDC)
    print('------------ %s ------------' % 'ANSWERS')
    print(answers)
    print('------------------------')

    session = requests_cache.CachedSession('query_cache') if data.get('is_testing', False) else None
    google_responses = grequests.map(build_google_queries(question, answers, session))
    wikipedia_responses = grequests.map(build_wikipedia_queries(question, answers, session))

    confidence = find_answer_words_google(question, answers, confidence, google_responses[:1])
    confidence = count_results_number_google(question, answers, confidence, google_responses[1:])
    confidence = find_question_words_wikipedia(question, answers, confidence, wikipedia_responses)

    # Calculate prediction
    prediction = min(confidence, key=confidence.get) if 'NOT' in question or 'NEVER' in question else max(confidence, key=confidence.get)
    total_occurrences = sum(confidence.values())
    for n, count in confidence.items():
        likelihood = int(count/total_occurrences * 100) if total_occurrences else 0
        confidence[n] = '%d%%' % likelihood
        result = 'Answer %s: %s - %s%%' % (n, answers[n], likelihood)
        print(colors.BOLD + result + colors.ENDC if n == prediction else result)

    return (prediction if confidence[prediction] else None, confidence)


# METHOD 1: Find answer in Google search result descriptions
def find_answer_words_google(question, answers, confidence, responses):

    occurrences = {'A': 0, 'B': 0, 'C': 0}
    response = responses[0]
    soup = BeautifulSoup(response.text, "html5lib")

    # Check for rate limiting page
    if '/sorry/index?continue=' in response.url:
        sys.exit('ERROR: Google rate limiting detected.')

    # Get search descriptions
    results = ''
    for g in soup.find_all(class_='st'):
        results += " " + g.text
    cleaned_results = results.strip().replace('\n','')
    results_words = get_raw_words(cleaned_results)

    # Find answer words in search descriptions
    for n, answer in answers.items():
        answer_words = get_raw_words(answer)
        occurrences[n] += results_words.count(answer_words)

    print("%s" % response.url)
    print("Count: %s%s%s" % (colors.BOLD, occurrences, colors.ENDC))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for n, count in occurrences.items():
        confidence[n] += int(count/total_occurrences * weights.GOOGLE_SUMMARY_ANSWER_COUNT) if total_occurrences else 0

    print("METHOD 1 - Confidence: %s" % confidence)
    return confidence


# METHOD 1: Find answer in Google search result descriptions
def method_1(question, answers):

    session = None
    google_responses = grequests.map([grequests.get('https://www.google.co.uk/search?q=' + urllib.parse.quote_plus(question), session=session)])
    response = google_responses[:1][0]

    occurrences = {'A': 0, 'B': 0, 'C': 0}
    confidence = {'A': 0, 'B': 0, 'C': 0}
    soup = BeautifulSoup(response.text, "html5lib")

    # Check for rate limiting page
    if '/sorry/index?continue=' in response.url:
        sys.exit('ERROR: Google rate limiting detected.')

    # Get search descriptions
    results = ''
    for g in soup.find_all(class_='st'):
        results += " " + g.text
    cleaned_results = results.strip().replace('\n','')
    results_words = get_raw_words(cleaned_results)

    # Find answer words in search descriptions
    for n, answer in answers.items():
        answer_words = get_raw_words(answer)
        occurrences[n] += results_words.count(answer_words)

    print("Count: %s%s%s" % (colors.BOLD, occurrences, colors.ENDC))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for n, count in occurrences.items():
        confidence[n] = int(count/total_occurrences * 100) if total_occurrences else 0

    return confidence


# METHOD 2: Compare number of results found by Google
def method_2(question, answers):

    queries = ['%s "%s"' % (question, answer) for answer in answers.values()]
    responses = grequests.map([grequests.get('https://www.google.co.uk/search?q=' + urllib.parse.quote_plus(q), session=None) for q in queries])

    occurrences = {'A': 0, 'B': 0, 'C': 0}
    confidence = {'A': 0, 'B': 0, 'C': 0}

    # Loop through search results
    for n, response in enumerate(responses):
        soup = BeautifulSoup(response.text, "html5lib")

        # Check for rate limiting page
        if '/sorry/index?continue=' in response.url:
            sys.exit('ERROR: Google rate limiting detected.')

        if soup.find(id='resultStats'):
            results_count_text = soup.find(id='resultStats').text.replace(',', '')
            if len(results_count_text) != 0 and len(re.findall(r'\d+', results_count_text)) != 0:
                results_count = re.findall(r'\d+', results_count_text)[0]
                occurrences[chr(65 + n)] += int(results_count)

        print("%s" % response.url)

    print("Search Results: %s%s%s" % (colors.BOLD, occurrences, colors.ENDC))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for n, count in occurrences.items():
        confidence[n] += int(count/total_occurrences * 100) if total_occurrences else 0

    return confidence


# METHOD 3: Find question words in wikipedia pages
def method_3(question, answers):

    responses = grequests.map(build_wikipedia_queries(question, answers, None))
    occurrences = {'A': 0, 'B': 0, 'C': 0}
    confidence = {'A': 0, 'B': 0, 'C': 0}

    # Get nouns from question words
    question_words = get_raw_words(question)
    question_nouns = get_text_nouns(question_words).split(' ')

    # Loop through wikipedia results
    for n, response in enumerate(responses):

        # Check for unresolved Wikipedia link
        if 'Special:Search' in response.url:
            return confidence

        # Get wikipedia page text elements
        results = ''
        soup = BeautifulSoup(response.text, "html5lib")
        for g in soup.find_all('p'):
            results += " " + g.text
        cleaned_results = results.strip().replace('\n','')
        results_words = get_raw_words(cleaned_results)

        # Find question words on wikipedia page
        occurrences_list = find_keywords(question_nouns, results_words)
        occurrences[chr(65 + n)] += sum(occurrences_list)

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for n, count in occurrences.items():
        confidence[n] += int(count/total_occurrences * 100) if total_occurrences else 0

    return confidence


# METHOD 2: Compare number of results found by Google
def count_results_number_google(question, answers, confidence, responses):

    occurrences = {'A': 0, 'B': 0, 'C': 0}

    # Loop through search results
    for n, response in enumerate(responses):
        soup = BeautifulSoup(response.text, "html5lib")
        if soup.find(id='resultStats'):
            results_count_text = soup.find(id='resultStats').text.replace(',', '')
            results_count = re.findall(r'\d+', results_count_text)[0]
            occurrences[chr(65 + n)] += int(results_count)

        print("%s" % response.url)

    print("Search Results: %s%s%s" % (colors.BOLD, occurrences, colors.ENDC))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for n, count in occurrences.items():
        confidence[n] += int(count/total_occurrences * weights.NUM_GOOGLE_RESULTS) if total_occurrences else 0

    print("METHOD 1 + 2 - Confidence: %s" % confidence)
    return confidence


# METHOD 3: Find question words in wikipedia pages
def find_question_words_wikipedia(question, answers, confidence, responses):

    occurrences = {'A': 0, 'B': 0, 'C': 0}

    # Get nouns from question words
    question_words = get_raw_words(question)
    question_nouns = get_text_nouns(question_words).split(' ')
    print('question_nouns: %s' % question_nouns)

    # Loop through wikipedia results
    for n, response in enumerate(responses):

        # Check for unresolved Wikipedia link
        if 'Special:Search' in response.url:
            print('METHOD 3 - SKIPPED: Unresolved Wikipedia link')
            return confidence

        # Get wikipedia page text elements
        results = ''
        soup = BeautifulSoup(response.text, "html5lib")
        for g in soup.find_all('p'):
            results += " " + g.text
        cleaned_results = results.strip().replace('\n','')
        results_words = get_raw_words(cleaned_results)

        # Find question words on wikipedia page
        occurrences_list = find_keywords(question_nouns, results_words)
        occurrences[chr(65 + n)] += sum(occurrences_list)
        print("%s: Score: %s" % (response.url, sum(occurrences_list)))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for n, count in occurrences.items():
        confidence[n] += int(count/total_occurrences * weights.WIKIPEDIA_PAGE_QUESTION_COUNT) if total_occurrences else 0

    print("METHOD 1 + 2 + 3 - Confidence: %s" % confidence)
    return confidence

# print out accuracy
def find_original_accuracy():
    all_question_count = 0
    all_correct_count = 0
    path = 'games/*.json'
    for filename in glob.glob(path):
        question_count = 0
        correct_count = 0
        game = json.load(open(filename))
        id = game.get('showId')
        for q in game.get('questions'):
            question_count = question_count + 1

            if q.get('correct') == q.get('prediction')['answer']:
                correct_count = correct_count + 1

        if question_count != 0:
            print(correct_count/question_count*100)
    if all_question_count != 0:
        print(all_correct_count/all_question_count*100)

# print out accuracy
def test_current_accuracy():
    all_question_count = 0
    all_correct_count = 0
    path = 'games/*.json'


    with open('./methods/google_question.json' % method_name) as file:
        method_1_json = json.load(file)
    with open('./methods/google_question_followed_by_answers.json' % method_name) as file:
        method_2_json = json.load(file)
    with open('./methods/find_question_words_on_answers_wikipedia_pages.json' % method_name) as file:
        method_3_json = json.load(file)

    for filename in glob.glob(path):
        question_count = 0
        correct_count = 0
        game = json.load(open(filename))
        id = game.get('showId')
        for q in game.get('questions'):
            question_count = question_count + 1

            #Get prediction from method_1 json
            method_1_json.get(str(id))

            #Get prediction from method_2 json

            #Get prediction from method_3 json

            #Combine weightings to get overall prediction

            if q.get('correct') == prediction:
                correct_count = correct_count + 1

        if question_count != 0:
            print(correct_count/question_count*100)
    if all_question_count != 0:
        print(all_correct_count/all_question_count*100)




def create_method_json(method,method_name):
    all_method_results = {}

    path = 'games/*.json'

    # Load saved method results
    with open('./methods/%s.json' % method_name) as file:
        output = json.load(file)

    for filename in glob.glob(path):
        game = json.load(open(filename))
        id = game.get('showId')

        if output.get(str(id)):
            print('already done %s' % id)
            continue

        game_method_results = {}
        for q in game.get('questions'):
            print('Game %s: Question: %s' % (id,q.get('questionNumber')))
            confidence = method(q.get('question'),q.get('answers'))
            game_method_results[q.get('questionNumber')] = confidence

        output[str(id)] = game_method_results

        # Update saved method results
        with open('./methods/%s.json' % method_name, 'w') as file:
            json.dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)

        print('Wrote to game %s' % id)



# Find keywords in specified data
def find_keywords(keywords, data):
    words_found = []
    for keyword in keywords:
        if len(keyword) > 2:
            if keyword in data and keyword not in words_found:
                words_found.append(data.count(keyword))
    return words_found


# Get nouns from text
def get_text_nouns(input):
    response = ''
    for (word, tag) in nltk.pos_tag(nltk.word_tokenize(input)):
        if tag.startswith('NN') or tag.startswith('NNP'):
            response += word + ' '
    return response.strip()


# Extract raw words from data
def get_raw_words(data):
    data = re.sub('[^\w ]', '' , data)
    words = data.replace('  ' , ' ').lower()
    return words
