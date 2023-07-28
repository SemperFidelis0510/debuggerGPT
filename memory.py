import json
import os


class Memory:
    def __init__(self):
        self.load()

    def load(self):
        files = os.listdir('memory')
        for file in files:
            if file.endswith('.json'):
                with open(f'memory/{file}', 'r') as f:
                    if os.stat(f'memory/{file}').st_size != 0:
                        setattr(self, file[:-5], json.load(f))
                    else:
                        setattr(self, file[:-5], {})
                if os.stat(f'memory/{file}').st_size == 0:
                    with open(f'memory/{file}', 'w') as f:
                        json.dump({}, f)

    def cache(self):
        files = os.listdir('memory')
        for file in files:
            if file.endswith('.json'):
                with open(f'memory/{file}', 'w') as f:
                    json.dump(getattr(self, file[:-5]), f)

    def __str__(self):
        return str(self.__dict__)

    def __contains__(self, key):
        return key in self.__dict__

    def __getitem__(self, key):
        return self.__dict__.get(key)

    def __setitem__(self, key, value):
        self.__dict__[key] = value
        self.cache()

    def to_json(self):
        return json.dumps(self.__dict__, indent=4)


class Plan:
    def __init__(self):
        self.plan = ''
        self.reduction = {}

    def __str__(self):
        return self.plan

    def reason(self):
        pass
