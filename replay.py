from glob import glob
from json import load, loads, dump, JSONDecodeError
from question import Question
from utils import predict_answers


class Replayer(object):
    """ One instance of the game Replayer """
    def __init__(self, game_paths=[]):
        self.questions = self.load_questions(game_paths)

    def load_questions(self, game_paths=[]):
        """ Create a list of Question objects to replay """
        questions = []
        if not game_paths:
            game_paths = [filename for filename in glob('games/*.json')]
        for game_path in game_paths:
            game_data = load(open(game_path))
            for question in game_data['questions']:
                questions.append(Question(**question))
        return questions

    def play(self):
        self.setup_output_file()
        for question in self.questions:
            result = predict_answers(question)
            print(result)

    def setup_output_file(self, mode='r+'):
        try:
            with open('replay_results.json', mode) as file:
                output = load(file) if mode == 'r+' else []
                output.append([])
                file.seek(0)
                dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)
        except FileNotFoundError:
            self.setup_output_file(mode='w+')
