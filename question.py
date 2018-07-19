from glob import glob
import os
from json import load, dump

class Question(object):
    """ An instance of a HQ Trivia question """

    def __init__(self, is_replay=False, load_id=None, **kwargs):

        self.is_replay = is_replay

        if load_id is not None:
            output_key = -1 if self.is_replay else 'questions'
            with open(self.game_path) as file:
                output = load(file)
            questions = output[output_key]
            kwarg_vals = next((q for q in questions if q["questionId"] == load_id), None)
            self.__init__(is_replay=is_replay, **kwarg_vals)

        self.id = kwargs.get('questionId', None)
        self.number = kwargs.get('questionNumber', None)
        self.text = kwargs.get('question', None)
        self.answers = kwargs.get('answers', None)
        self.correct = kwargs.get("correct", None)
        self.category = kwargs.get("category", None)
        self.prediction = kwargs.get("prediction", {})
        self.correct = kwargs.get("correct", None)


    @property
    def game_path(self):
        """ Determine what file to save question in """
        path = 'replay_results.json'

        if self.is_replay is False:
            game_files = glob('games/*.json')
            path = max(game_files, key=os.path.getctime)

        return path


    def save(self):
        """
        Checks most recently created results file, checks it for question with same id.
        If present, updates. If not, appends itself. File path used depends on
        whether is_replay is True or False
        """
        output_key = -1 if self.is_replay else 'questions' # last list in replay games or 'questions' key in live saved games

        with open(self.game_path) as file:
            output = load(file)

        # pull questions out of file
        questions = output[output_key]

        updated = False
        for idx, saved_question in enumerate(questions):
            if saved_question['questionId'] == self.id:
                questions[idx] = self._dict_for_json()
                updated = True
                break
        if updated is False:
            questions.append(self._dict_for_json())

        # re-insert updated questions
        output[output_key] = questions

        # Update save game file
        with open(self.game_path, 'w') as file:
            dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)

    def display_summary(self):
        pass

    def add_prediction(self, prediction, confidence):
        """ Add the prediction dict to the Question """
        self.prediction = {
            'answer': prediction,
            'confidence': confidence
        }
        self.save()

    def add_correct(self, correct):
        """ Add correct answer to question and save """
        self.correct = correct
        self.save()

    def _dict_for_json(self):
        """ Convert instance to dict with correct keys in preparation for saving to JSON """
        output = vars(self).copy()
        output['questionId'] = output.pop('id', None)
        output['questionNumber'] = output.pop('number', None)
        output['question'] = output.pop('text', None)
        output.pop('is_replay')
        return output
