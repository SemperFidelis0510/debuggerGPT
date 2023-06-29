import json


class Memory:
    def __init__(self):
        self.memory = {}
        self.aliases = {}

    def __str__(self):
        return str(self.memory)

    def __repr__(self):
        return repr(self.memory)

    def __getitem__(self, key):
        return self.recall(key)

    def __setitem__(self, key, value):
        self.remember(key, value)

    def __contains__(self, key):
        return key in self.memory or key in self.aliases

    def remember(self, key, value, nature='memory'):
        if nature == 'memory':
            self.memory[key] = value
        elif nature == 'alias':
            self.aliases[key] = value

    def recall(self, key):
        return self.memory.get(key, self.aliases.get(key))

    def cache(self):
        with open('memory.json', 'w') as f:
            json.dump({'memory': self.memory, 'aliases': self.aliases}, f)

    def load(self):
        with open('memory.json', 'r') as f:
            data = json.load(f)
            self.memory = data.get('memory', {})
            self.aliases = data.get('aliases', {})
