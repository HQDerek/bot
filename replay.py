""" Module for replaying a given game """
from glob import glob
from json import load, dump
from question import Question
from utils import predict_answers

class Replayer(object):
    """ One instance of the game Replayer """
    def __init__(self, game_paths=None):
        self.questions = self.load_questions(game_paths)

    @staticmethod
    def load_questions(game_paths=None):
        """ Create a list of Question objects to replay """
        questions = []
        if not game_paths:
            game_paths = [filename for filename in glob('games/*.json')]
        for game_path in game_paths:
            game_data = load(open(game_path))
            for question in game_data['questions']:
                questions.append(Question(is_replay=True, **question))
        return questions

    def play(self):
        """ Play all questions loaded from saved games """
        self.setup_output_file()
        for question in self.questions:
            (prediction, confidence) = predict_answers(question)
            question.add_prediction(prediction, confidence)

    def setup_output_file(self, mode='r+'):
        """ Create or load replayer output file """
        try:
            with open('replay_results.json', mode) as file:
                output = load(file) if mode == 'r+' else []
                output.append([])
                file.seek(0)
                dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)
        except FileNotFoundError:
            self.setup_output_file(mode='w+')
