import re
import nltk
import grequests
import urllib.parse
from bs4 import BeautifulSoup

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

    return list(map(lambda q: grequests.get('https://www.google.ca/search?q=%s' % urllib.parse.quote_plus(q)), queries))


# Get answer predictions
def predict_answers(question, answers):

    print('------------ %s ------------' % 'QUESTION')
    print(question)
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

    total_occurences = sum(counts.values())
    sorted_counts = [(n, counts[n]) for n in sorted(counts, key=counts.get, reverse=True)]
    prediction = sorted_counts[0][0]

    for (n, count) in sorted_counts:
        likelihood = int(count/total_occurences * 100) if total_occurences else 0
        print('Answer %s: %s - %s%%' % (n, answers[n], likelihood))

    return prediction if sorted_counts[0][1] else None
