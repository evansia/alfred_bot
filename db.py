from tinydb import TinyDB, Query, where

class DB:
    def __init__(self):
        self.db = TinyDB('data/db.json')

    def insert(self, values):
        self.db.insert(values)

    def fetch_all(self):
        return self.db.all()

    def fetch_on_call_rota(self):
        res = {}
        rec = self.db.all()
        rec = sorted(rec, key=lambda  k: k['order'])
        for idx, r in enumerate(rec):
            if r['is_on_call'] == 1:
                res['current'] = r
                res['previous'] = rec[idx-1] if idx > 0 else rec[-1]
                res['next'] = rec[idx+1] if idx < len(rec) - 1 else rec[0]
                break
        return res

    def update(self, key, values):
        rec = self.db.search(where('name') == key)
        if not rec:
            return False
        rec[0].update(values)
        self.db.write_back(rec)
        return True


if __name__ == '__main__':
    db = DB()
    print(db.fetch_on_call_rota())