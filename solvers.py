""" Solvers for the HQ Trivia bot project """
import re
import sys
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from utils import Colours, get_raw_words, get_significant_words


class BaseSolver(object):
    """ an instance of a question solver to return answer confidences """

    weight = 0
    service_url = None

    @staticmethod
    def build_queries(question_text, answers):
        """ build queries with question text and answers """
        raise NotImplementedError()

        queries = {}
        for answer_key, answer_value in answer.values():
            queries[answer_key] = '%s "%s"' % (question_text, answer_key)
        return queries


    def build_urls(self, question_text, answers):
        """ build URLs with search queries """
        urls = {}
        queries = self.build_queries(question_text.replace(' NOT ', ' ').replace(' NEVER ', ' '), answers)

        for answer_key, query_string in queries.items():
            urls[answer_key] = self.service_url.format(quote_plus(query_string))

        return urls

    @staticmethod
    def fetch_responses(urls, session):
        """ fetch responses for solver URLs """
        import pdb; pdb.set_trace()
        responses = {}
        for answer_key, url in urls.items():
            responses[answer_key] = session.get(url)
        return responses

    def get_answer_matches(self, response, index, answers, matches):
        """ get answer occurences for response """
        raise NotImplementedError()

    def compute_confidence(self, matches, confidence):
        """ Calculate confidence for matches """
        total_matches = sum(matches.values())
        if total_matches:
            for index, count in matches.items():
                confidence[index] += int(((count / total_matches) * 100) * self.weight)
        return confidence

    @staticmethod
    def choose_answer(question_text, confidence):
        """ Choose an answer using confidence """
        if sum(confidence.values()) == 0:
            return 'A'
        comparison = min if ' NOT ' in question_text or ' NEVER ' in question_text else max
        return comparison(confidence, key=confidence.get)

    def run(self, question_text, answers, responses, confidence):
        """ Run solver and return confidence """

        print('\n%s: ' % (re.sub(r'(\w)([A-Z])', r'\1 \2', self.__class__.__name__)[:-7]))

        matches = {'A': 0, 'B': 0, 'C': 0}

        for answer_key, response in responses.items():
            response = response.result() if hasattr(response, 'result') else response
            if '/sorry/index?continue=' in response.url:
                sys.exit('ERROR: Google rate limiting detected.')
            matches = self.get_answer_matches(response, answer_key, answers, matches)

        confidence = self.compute_confidence(matches, confidence)
        prediction = self.choose_answer(question_text, confidence)

        return prediction, confidence


class GoogleAnswerWordsSolver(BaseSolver):
    """ Solver that searches question on Google and counts answers in results """

    weight = 200
    full_answer_weight = 1000
    partial_answer_weight = 100
    service_url = 'https://www.google.co.uk/search?pws=0&q={}'

    @staticmethod
    def build_queries(question_text, answers):
        """ build queries with question text and answers """
        return {'_': question_text}

    def get_answer_matches(self, response, _, answers, matches):
        """ get answer occurences for response """
        results = ''
        document = BeautifulSoup(response.text, "html5lib")
        for element in document.find_all(class_='st'):
            results += " " + element.text # Search result descriptions
        for element in document.find_all(class_='r'):
            results += " " + element.text # Search result titles
        for element in document.find_all(class_='mod'):
            results += " " + element.text # Quick answer card
        for element in document.find_all(class_='brs_col'):
            results += " " + element.text # Related searches
        results_words = get_raw_words(results)
        print('Exact matches: ')
        for answer_key, answer in answers.items():
            count = results_words.count(' {} '.format(get_raw_words(answer)))
            matches[answer_key] += self.full_answer_weight * count
            print('{}: {}'.format(answer_key, Colours.BOLD.value + str(count) + Colours.ENDC.value))
        print('\nPartial matches: ')
        for answer_key, answer in answers.items():
            count = 0
            for word in get_significant_words(get_raw_words(answer)):
                count += results_words.count(' {} '.format(word))
            matches[answer_key] += self.partial_answer_weight * count
            print('{}: {}'.format(answer_key, Colours.BOLD.value + str(count) + Colours.ENDC.value))
        return matches


class GoogleResultsCountSolver(BaseSolver):
    """ Solver that searches question with quoted answer on Google and compares the number of results """

    weight = 100
    service_url = 'https://www.google.co.uk/search?pws=0&q={}'

    @staticmethod
    def build_queries(question_text, answers):
        """ build queries dict with question text and answers """
        queries = {}
        for answer_key, answer_value in answers.items():
            queries[answer_key] = '%s "%s"' % (question_text, answer_key)
        return queries

    def get_answer_matches(self, response, answer_key, answers, matches):
        """ get answer occurences for response """
        document = BeautifulSoup(response.text, "html5lib")
        if getattr(document.find(id='topstuff'), 'text', '')[:16] != 'No results found':
            if document.find(id='resultStats'):
                results_count_text = document.find(id='resultStats').text.replace(',', '')
                results_count = re.findall(r'\d+', results_count_text)
                if results_count:
                    matches[answer_key] += int(results_count[0])
        print('{}: {}{:,}{}'.format(
            answer_key, Colours.BOLD.value, matches[answer_key], Colours.ENDC.value
        ))
        return matches
