""" Module for replaying a given game """
from glob import glob
from json import load, dump
from question import Question
from utils import predict_answers
from pandas import DataFrame
import os
import webbrowser

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

    def gen_report(self):
        try:
            with open('replay_results.json', 'r') as file:
                replays = load(file)
                max_q_index = len(replays[0]) - 1
                trimmed_replays = [replay[:max_q_index] if len(replay) > (max_q_index + 1) else replay for replay in replays]
        except FileNotFoundError:
            raise Exception("No game results to generate replay report")
        headers = ['Q{}'. format(i + 1) for i in range(max_q_index + 1)]
        run_results = []
        for index, replay in enumerate(trimmed_replays):
            run_result = []
            if index == 0:
                # is first 'master' game - no comparison needed
                run_result = [0] * len(replay)
            else:
                for q_idx, question_kwargs in enumerate(replay):
                    question = Question(is_replay=True, **question_kwargs)
                    try:
                        if question.prediction['answer'] == trimmed_replays[0][q_idx]['prediction']['answer']:
                            run_result.append(0)
                        elif question.answered_correctly:
                            run_result.append(1)
                        else:
                            run_result.append(-1)
                    except IndexError:
                            run_result.append(0)

            run_results.append(run_result)
        df = DataFrame(columns=headers, data=run_results)
        html = '<html>{}</html>'.format(df.to_html())
        path = os.path.abspath('replay_report.html')
        url = 'file://' + path

        with open(path, 'w') as f:
            f.write(html)
        webbrowser.open(url)
