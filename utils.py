import re
import nltk
import requests_cache
import grequests
import urllib.parse
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
    queries = [get_text_nouns(answer) for answer in list(answers.values())]

    return [grequests.get('https://en.wikipedia.org/wiki/Special:Search?search=' + urllib.parse.quote_plus(q), session=session) for q in queries]


# Get answer predictions
def predict_answers(data, answers):

    confidence = {
        'A': 0,
        'B': 0,
        'C': 0
    }
    question = data.get('question')

    print('------------ %s %s | %s ------------' % ('QUESTION', data.get('questionNumber'), data.get('category')))
    print(colors.BOLD + question + colors.ENDC)
    print('------------ %s ------------' % 'ANSWERS')
    print(answers)
    print('------------------------')

    session = requests_cache.CachedSession('query_cache') if data.get('is_testing') else None
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
    soup = BeautifulSoup(response.text, 'lxml')

    # Get search descriptions
    results = ''
    for g in soup.find_all(class_='st'):
        results += " " + g.text
    cleaned_results = results.strip().replace('\n','')
    results_words = get_raw_words(cleaned_results)

    # Find answer words in search descriptions
    for n, answer in answers.items():
        answer_words = get_raw_words(answer)
        occurrences[n] += results_words.count(answer)

    print("%s: Scores: %s" % (response.url, occurrences))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for n, count in occurrences.items():
        confidence[n] += int(count/total_occurrences * 100) if total_occurrences else 0

    print("METHOD 1 - Confidence: %s" % confidence)
    return confidence


# METHOD 2: Compare number of results found by Google
def count_results_number_google(question, answers, confidence, responses):

    occurrences = {'A': 0, 'B': 0, 'C': 0}

    # Loop through search results
    for n, response in enumerate(responses):
        soup = BeautifulSoup(response.text, 'lxml')
        if soup.find(id='resultStats'):
            results_count_text = soup.find(id='resultStats').text.replace(',', '')
            results_count = re.findall(r'\d+', results_count_text)[0]
            occurrences[chr(65 + n)] += int(results_count)

        print("%s: Scores: %s" % (response.url, occurrences))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for n, count in occurrences.items():
        confidence[n] += int(count/total_occurrences * 100) if total_occurrences else 0

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

        # Get wikipedia page text elements
        results = ''
        soup = BeautifulSoup(response.text, 'lxml')
        for g in soup.find_all('p'):
            results += " " + g.text
        cleaned_results = results.strip().replace('\n','')
        results_words = get_raw_words(cleaned_results)

        # Find question words on wikipedia page
        occurrences_list = find_keywords(question_nouns, results_words)
        occurrences[chr(65 + n)] += sum(occurrences_list) * 100
        print("%s: Score: %s" % (response.url, sum(occurrences_list) * 100))

    # Calculate confidence
    total_occurrences = sum(occurrences.values())
    for n, count in occurrences.items():
        confidence[n] += int(count/total_occurrences * 100) if total_occurrences else 0

    print("METHOD 1 + 2 + 3 - Confidence: %s" % confidence)
    return confidence


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
    words = data.replace('  ' , ' ')
    return words
