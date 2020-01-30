from tinydb import TinyDB, Query, where

class DB:
    def __init__(self):
        self.db = TinyDB('data/db.json')

    def fetch_data(self, field, key):
        return self.fetch('data', field, key)

    def fetch_metadata(self, field, key):
        return self.fetch('metadata', field, key)

    def fetch(self, table, field, key):
        tbl = self.db.table(table)
        return tbl.search(where(field) == key)

    def fetch_all_data(self):
        return self.fetch_all('data')

    def fetch_all_metadata(self):
        return self.fetch_all('metadata')

    def fetch_all(self, table):
        tbl = self.db.table(table)
        return tbl.all()

    def update_data(self, field, key, value):
        return self.update('data', field, key, value)

    def update_metadata(self, field, key, value):
        return self.update('metadata', field, key, value)

    def update(self, table, field, key, value):
        tbl = self.db.table(table)
        rec = tbl.search(where(field) == key)
        if not rec:
            return False
        rec[0].update(value)
        tbl.write_back(rec)
        return True


if __name__ == '__main__':
    db = DB()
    print(db.fetch_on_call_rota())