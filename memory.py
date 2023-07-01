import json


class Memory:
    def __init__(self):
        self.memory = {}
        self.aliases = {}
        self.data = {}

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        return {'memory': self.memory, 'aliases': self.aliases, 'data': self.data}

    def __getitem__(self, key):
        return self.recall(key)

    def __setitem__(self, key, value):
        self.remember(key, value)
        self.cache()

    def __contains__(self, key):
        return (key in self.memory) or (key in self.aliases) or (key in self.data)

    def remember(self, key, value, nature='memory'):
        if nature == 'memory':
            self.memory[key] = value
        elif nature == 'alias':
            self.aliases[key] = value
        elif nature == 'data':
            self.data[key] = value

    def recall(self, key):
        if key in self.memory:
            return self.memory[key]
        elif key in self.aliases:
            return self.aliases[key]
        elif key in self.data:
            return self.data[key]

    def cache(self):
        with open('memory/memory.json', 'w') as f:
            json.dump({'memory': self.memory, 'aliases': self.aliases, 'data': self.data}, f)

    def load(self):
        with open('memory/memory.json', 'r') as f:
            data = json.load(f)
            self.memory = data.get('memory', {})
            self.aliases = data.get('aliases', {})
            self.data = data.get('data', {})

    def to_json(self):
        return json.dumps({'memory': self.memory, 'aliases': self.aliases, 'data': self.data}, indent=4)


class Plan:
    def __init__(self):
        self.plan = ''
        self.reduction = {}

    def __str__(self):
        return self.plan

    def reason(self):
        pass

    def cache(self):
        with open('memory/memory.json', 'w') as f:
            json.dump({'memory': self.memory, 'aliases': self.aliases, 'data': self.data}, f)

    def load(self):
        with open('memory/memory.json', 'r') as f:
            data = json.load(f)
            self.memory = data.get('memory', {})
            self.aliases = data.get('aliases', {})
            self.data = data.get('data', {})

    def to_json(self):
        return json.dumps({'memory': self.memory, 'aliases': self.aliases, 'data': self.data}, indent=4)
