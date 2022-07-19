import redis


class Database(object):

    def __init__(self, database_host, database_port, database_password):
        self.db = redis.Redis(
            host=database_host, port=database_port, password=database_password
        )

    def set_(self, field, value):
        self.db.set(field, value)

    def get(self, field):
        value = self.db.get(field)
        return value

