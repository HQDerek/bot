""" Solvers for the HQ Trivia bot project """
import re
import sys
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from utils import get_raw_words


class BaseSolver(object):
    """ an instance of a question solver to return answer confidences """

    weight = 0
    service_url = None

    def build_queries(self, question_text, answers):
        """ build queries with question text and answers """
        raise NotImplementedError()

    def build_urls(self, question_text, answers):
        """ build URLs with search queries """
        queries = self.build_queries(question_text, answers)
        return [self.service_url.format(quote_plus(query)) for query in queries]

    def fetch_responses(self, urls, session):
        """ fetch responses for solver URLs """
        return [(resp.result() if hasattr(resp, 'result') else resp) for resp in map(session.get, urls)]

    def get_answer_matches(self, response, answers, matches):
        """ get answer occurences for response """
        raise NotImplementedError()

    def compute_confidence(self, matches, confidence):
        """ Calculate confidence for matches """
        total_matches = sum(matches.values())
        if total_matches:
            for index, count in matches.items():
                confidence[index] += int(((count / total_matches) * 100) * self.weight)
        return confidence

    def choose_answer(self, question_text, confidence):
        """ Choose an answer using confidence """
        comparison = min if 'NOT' in question_text or 'NEVER' in question_text else max
        return comparison(confidence, key=confidence.get)

    def run(self, question_text, answers, session, confidence):
        """ Run solver and return confidence """

        matches = {'A': 0, 'B': 0, 'C': 0}
        urls = self.build_urls(question_text, answers)

        for response in self.fetch_responses(urls, session):
            if '/sorry/index?continue=' in response.url:
                sys.exit('ERROR: Google rate limiting detected.')
            matches = self.get_answer_matches(response, answers, matches)

        confidence = self.compute_confidence(matches, confidence)
        prediction = self.choose_answer(question_text, confidence)
        return prediction, confidence


class GoogleAnswerWordsSolver(BaseSolver):
    """ Solver that searches question on Google and counts answers in results """

    weight = 200
    service_url = 'https://www.google.co.uk/search?pws=0&q={}'

    def build_queries(self, question_text, answers):
        """ build queries with question text and answers """
        return [question_text]

    def get_answer_matches(self, response, answers, matches):
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
        for index, answer in answers.items():
            answer_words = get_raw_words(answer)
            matches[index] += results_words.count(answer_words)
        return matches


class GoogleResultsCountSolver(BaseSolver):
    """ Solver that searches question with quoted answer on Google and compares the number of results """

    weight = 100
    service_url = 'https://www.google.co.uk/search?pws=0&q={}'

    def build_queries(self, question_text, answers):
        """ build queries with question text and answers """
        return ['%s "%s"' % (question_text, answer) for answer in answers.values()]

    def fetch_responses(self, urls, session):
        """ fetch responses for solver URLs and add answer indexes """
        responses = super().fetch_responses(urls, session)
        for index, response in enumerate(responses):
            response.index = index
        return responses

    def get_answer_matches(self, response, answers, matches):
        """ get answer occurences for response """
        document = BeautifulSoup(response.text, "html5lib")
        if document.find(id='resultStats'):
            results_count_text = document.find(id='resultStats').text.replace(',', '')
            results_count = re.findall(r'\d+', results_count_text)
            if results_count:
                matches[chr(65 + response.index)] += int(results_count[0])
        return matches
