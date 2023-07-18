import json
import os
import subprocess
import re
import time
import openai


class Instructor:
    def __init__(self):
        self.tutorials = {}
        self.tut_counter = {}
        self.passed = {}
        self.plan_stage = 0
        self.plan_depth = 5
        self.one_time = ['init']

        self.load_instructions()

    def __call__(self, *args, **kwargs):
        if len(args) == 1:
            return self.teach(args[0])
        else:
            return None

    def load_instructions(self):
        instructions_dir = 'ai_instructions'
        for filename in os.listdir(instructions_dir):
            if filename.endswith('.txt'):
                tutorial_name = filename[:-4]
                with open(os.path.join(instructions_dir, filename), 'r') as file:
                    instructions = file.read()
                self.tutorials[tutorial_name] = instructions
                self.passed[tutorial_name] = False
                self.tut_counter[tutorial_name] = 0

    def teach(self, subject):
        self.done(subject)
        if subject == 'plan':
            self.plan_stage += 1
            if self.plan_stage >= self.plan_depth:
                return ''
        return self.tutorials[subject]

    def done(self, subject):
        self.tut_counter[subject] += 1
        self.passed[subject] = True
        if (subject == 'edit_file') and (self.tut_counter[subject] >= 3):
            self.tut_counter[subject] = 0
            self.passed[subject] = False


class Code:
    def __init__(self, code='', output=None, error=None, path=None):
        self.code = code
        self.code_lines = code.split('\n')
        self.output = output
        self.error = error
        self.fixes = []
        self.path = ''
        self.debug_model = 'gpt-4'

        if path is not None:
            self.from_file(path)

    def to_json(self):
        return {
            'code': self.code,
            'output': self.output,
            'error': self.error
        }

    def load(self, path):
        with open(path, 'r') as file:
            self.code = file.read()
            lines = file.readline()

        i = 0
        for line in lines:
            i += 1
            self.code_lines[i] = line.replace('\n', '')

    @staticmethod
    def from_json(json_obj):
        return Code(json_obj['code'], json_obj['output'], json_obj['error'])

    def fix(self, lines, new_code):
        new_code = new_code.split('\n')
        if len(lines) == 1:
            lines = [lines[0], lines[0]]
        elif len(lines) == 0:
            if new_code == '':
                print('No fix is needed')
                return
            else:
                print('A new code was given, but instructions of where to put it are missing.')
                return
        j = 0
        for i in range(lines[0] - 1, lines[1]):
            self.code_lines[i] = new_code[j]
            j += 1
        self.compile_code()

    def compile_code(self):
        self.code = '\n'.join(self.code_lines)

    def debug(self):
        input_json = self.to_json()
        prompt = f"""
        You are a code debugger. Here is the code, its output, and the error it produced:

        {json.dumps(input_json, indent=4)}

        Please identify the lines that need to be changed and suggest the new code to fix the issue. 
        Return your response in the following JSON format:

        {{
            "lines": [start_line, end_line],
            "new_code": "the new code",
            "align": number of idents at the beginning of this code snippet
        }}

        Note to yourself:
        - If there is only one line to be changed, the value on the key "lines", will be as [change_line, change_line], i.e both elements of the list will be the same single line.
        - Add nothing else to you response, send only the JSON.
        - The content of this prompt might be divided into a few parts, and be sent in a sequence. 
        Therefore, you should not send any response back, until you receive the total prompt. To know when the prompt is complete,
        expect the total content of this complete prompt to end with only the JSON with keys {{'code','output','error'}}.
        """

        prompt_parts = [prompt[i:i + 4097] for i in range(0, len(prompt), 4097)]
        responses = []
        for part in prompt_parts:
            response = openai.ChatCompletion.create(
                model=self.debug_model,
                messages=[
                    {"role": "system",
                     "content": "You are an experienced Python coder. You want to help the user debug his codes."},
                    {"role": "user",
                     "content": part}
                ]
            )
            responses.append(response['choices'][0]['message']['content'])

        content = ''.join(responses)

        try:
            # Use a regex to extract the JSON object from the response
            match = re.search(r'\{\s*"lines":\s*\[.*],\s*"new_code":\s*".*"\s*}', content, re.DOTALL)
            if match:
                json_str = match.group(0)
                response_json = json.loads(json_str)
            else:
                print("No JSON object found in the response.")
                response_json = {'lines': [], 'new_code': ''}
        except json.JSONDecodeError:
            print("The content could not be parsed as JSON.")
            response_json = {'lines': [], 'new_code': ''}

        self.fix(response_json["lines"], response_json["new_code"])

    def to_file(self):
        path = self.path
        # Rename the old file if it exists
        if os.path.exists(path):
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            os.rename(path, f"{path}_{timestamp}")

        with open(path, "w") as f:
            for line in self.code:
                f.write(line)

    def from_file(self, path):
        self.path = path
        # Read the code from the file
        with open(self.path, 'r') as f:
            self.code = f.read()

    def run(self, env_name, args=''):
        args = args.split(' ')
        try:
            # Run the Python file in the specified conda environment
            result = subprocess.run(['conda', 'run', '-n', env_name, 'python', self.path] + args,
                                    capture_output=True,
                                    text=True)
            self.output = result.stdout
            self.error = result.stderr
        except Exception as e:
            self.output = ''
            self.error = str(e)


class Plan:
    depth = 3

    def __init__(self, plan):
        self.master_plan = plan
        self.scheme = {}

        self.devise()

    def devise(self):
        # This function divides the plan a few times up to the wanted depth.
        for i in range(self.depth):
            self.reduce()

    def reduce(self):
        # This function uses GPT-3 to divide the plan into smaller plans. The smaller plans should be also objects of this class. With the same master plan. they will be saved into the dictionary self.scheme.
        # when GPT-3 is prompted to divide the plan, it should also have the complete chat history that shows the total plan.

        # Initialize the OpenAI API with your secret key
        openai.api_key = 'your-api-key'

        # Define a pre-prompt to instruct the model to divide the plan
        pre_prompt = "Given the following master plan, please divide it into smaller, manageable subplans:\n"

        # Use the OpenAI API to generate a response
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=pre_prompt + self.master_plan,
            temperature=0.5,
            max_tokens=100
        )

        # The response.choices[0].text contains the generated text. We can split this into smaller plans.
        smaller_plans = response.choices[0].text.split('\n')

        # Create new Plan objects for each smaller plan and add them to the scheme
        for i, plan in enumerate(smaller_plans):
            self.scheme[i] = Plan(plan)
