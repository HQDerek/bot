import json
import glob
import os

# print out accuracy
def find_lifetime_game_accuracy():
    all_question_count = 0
    all_correct_count = 0
    path = 'games/*.json'
    for filename in glob.glob(path):
        question_count = 0
        correct_count = 0
        game = json.load(open(filename))
        id = game.get('showId')
        for q in game.get('questions'):
            question_count += 1
            all_question_count += 1

            if q.get('correct') == q.get('prediction')['answer']:
                correct_count += 1
                all_correct_count += 1

        # To print out accuracy of each game:
        #if question_count != 0:
            #print(correct_count/question_count*100)
    if all_question_count != 0:
        print("Overall lifetime accuracy: %d" % (all_correct_count/all_question_count*100))


# TODO: fix this to be scalable for more methods
# Cycles through various weight combinations (0->max x 0->max... x 0->max) and returns the best
def find_best_weights(methods):
    best_result = 0
    best_result_weights = [0,0,0]

    # Cycle through various weight combinations (0->300 x 0->300 x 0->300) to find the best
    for x in range(0,30):
        methods[0]['weight'] = x*10
        print('%s: best_result %s' % (x,best_result))
        for y in range(0,30):
            methods[1]['weight'] = y*10
            print('y Round %s' % y)
            for z in range(0,30):
                methods[2]['weight'] = z*10
                result = test_current_accuracy(methods)
                if result > best_result:
                    best_result = result
                    best_result_weights = [x,y,z]

    print(best_result)
    print(best_result_weights)

    return best_result_weights


# Returns the current accuracy
def test_current_accuracy(methods):
    all_question_count = 0
    all_correct_count = 0
    path = 'games/*.json'

    # Open each method json
    method_jsons = [None] * len(methods)
    for m, method in enumerate(methods):
        with open('./methods/%s.json' % method.get('name')) as file:
            method_jsons[m] = json.load(file)

    # Find the accuracy for every question of every game
    for filename in glob.glob(path):
        question_count = 0
        correct_count = 0
        game = json.load(open(filename))
        id = game.get('showId')
        for n, question in enumerate(game.get('questions')):

            try:
                # Get confidence of each method
                confidences = [None] * len(methods)
                for m, method_json in enumerate(method_jsons):
                    confidences[m] = method_json.get(str(id)).get(str(n+1))
                    confidences[m] = {k: v*methods[m].get('weight') for k, v in confidences[m].items()}

                question_count += 1

                # Combine weightings to get overall confidence
                total_occurrences = 0
                for confidence in confidences:
                    total_occurrences = total_occurrences + sum(confidence.values())
                overall_confidence = {"A":0,"B":0,"C":0}

                total_A = 0
                for confidence in confidences:
                    total_A = total_A + confidence.get('A')
                overall_confidence['A'] = int(total_A/total_occurrences * 100) if total_occurrences else 0

                total_B = 0
                for confidence in confidences:
                    total_B = total_B + confidence.get('B')
                overall_confidence['B'] = int(total_B/total_occurrences * 100) if total_occurrences else 0

                total_C = 0
                for confidence in confidences:
                    total_C = total_C + confidence.get('C')
                overall_confidence['C'] = int(total_C/total_occurrences * 100) if total_occurrences else 0

                #Calculate prediction
                prediction = min(overall_confidence, key=overall_confidence.get) if 'NOT' in question or 'NEVER' in question else max(overall_confidence, key=overall_confidence.get)
                if question.get('correct') == prediction:
                    correct_count += 1

            except Exception as e:
                #print("Error while testing Game %s, Q%s:\n%s" % (id,n+1,e))
                pass

        if question_count == 0:
            print("Please run update_method_jsons() to update the method files.")
            return 0

        all_question_count += question_count
        all_correct_count += correct_count

    if all_question_count != 0:
        return int(all_correct_count/all_question_count*100)
    else:
        return 0


def update_method_jsons(methods):
    for method in methods:
        create_method_json(method.get('method'), method.get('name'))


# Write all correct answers from games to correct_answers.json
def update_correct_answers_json():
    all_correct_answers = {}

    path = 'games/*.json'
    for filename in glob.glob(path):
        game = json.load(open(filename))
        id = game.get('showId')
        game_correct_answers = {}
        for q in game.get('questions'):
            game_correct_answers[q.get('questionNumber')] = q.get('correct')

        all_correct_answers[id] = game_correct_answers

    if not os.path.isfile('/methods/correct_answers.json'):
        with open('./methods/correct_answers.json', 'w') as file:
            json.dump(all_correct_answers, file, ensure_ascii=False, sort_keys=True, indent=4)


# Creates a json of confidence results for a method
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
            continue # This game has already been saved for this method

        game_method_results = {}
        for q in game.get('questions'):
            confidence = method(q.get('question'),q.get('answers'))
            print('Game %s, Question %s: %s' % (id,q.get('questionNumber'),confidence))
            game_method_results[q.get('questionNumber')] = confidence

        output[str(id)] = game_method_results

        # Update saved method results
        with open('./methods/%s.json' % method_name, 'w') as file:
            json.dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)

        print('Wrote game %s to %s.json' % (id,method_name))
