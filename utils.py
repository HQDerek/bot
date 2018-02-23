import re
import nltk
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


# Build query set from data and options
def build_queries(question, answers):
    queries = [question]

    #queries.append(get_question_nouns(question))
    #queries.append('%s "%s"' % (question, '"  "'.join(str(answers[index]) for index in sorted(answers))))
    for n, answer in answers.items():
        queries.append('%s "%s"' % (question, answer))

    google = list(map(lambda q: grequests.get('https://www.google.ca/search?q=%s' % urllib.parse.quote_plus(q)), queries))
    wikipedia = list(map(lambda q: grequests.get('https://en.wikipedia.org/wiki/Special:Search?search=%s' % urllib.parse.quote_plus(q)), list(answers.values())))

    return google + wikipedia

# Get answer predictions
def predict_answers(question, answers):

    print('------------ %s ------------' % 'QUESTION')
    print(colors.BOLD + question + colors.ENDC)
    print('------------ %s ------------' % 'ANSWERS')
    print(answers)
    print('------------------------')

    queries = build_queries(
        question,
        answers
    )
    responses = grequests.map(queries)
    return handle_responses(question, answers, responses)


# Find keywords in specified data
def find_keywords(keywords, data):
    words_found = []
    for keyword in keywords:
        if len(keyword) > 2:
            if keyword in data and keyword not in words_found:
                words_found.append(keyword)
    return words_found


# Get nouns from question
def get_question_nouns(question):
    response = ''
    for (word, tag) in nltk.pos_tag(nltk.word_tokenize(question)):
        if tag == 'NN' or tag == 'NNP':
            response += word + ' '
    return response.strip()


# Extract raw words from data
def get_raw_words(data):
    data = re.sub('[^\w ]', '' , data)
    words = data.replace('  ' , ' ')
    return words


# Handle question responses
def handle_responses(question, answers, responses):

    counts = {
        'A': 0,
        'B': 0,
        'C': 0
    }

    # Loop through search results
    for response in responses:
        print(response.url)

        # Extract search description text
        results = ''
        soup = BeautifulSoup(response.text, 'lxml')
        for g in soup.find_all(class_='st'):
            results += " " + g.text
        cleaned_results = results.strip().replace('\n','')
        results_words = get_raw_words(cleaned_results)
        #print('results_words: %s' % results_words)

        # Find answer in result descriptions
        for n, answer in answers.items():
            answer_words = get_raw_words(answer)    
            occurences = results_words.count(answer)
            #print('answer_words: %s' % answer_words)
            #print('occurences: %s' % occurences)
            counts[n] += occurences

    prediction = max(counts, key=counts.get)
    total_occurences = sum(counts.values())

    for n, count in counts.items():
        likelihood = int(count/total_occurences * 100) if total_occurences else 0
        result = 'Answer %s: %s - %s%%' % (n, answers[n], likelihood)
        print(colors.BOLD + result + colors.ENDC if n == prediction else result)

    return prediction if counts[prediction] else None
