import os
import pandahouse


class Getch:
    def __init__(self, query):
        self.connection = {
            'host': os.environ.get('CH_DB_HOST'),
            'password': os.environ.get('CH_DB_PASSWORD'),
            'user': os.environ.get('CH_DB_USER')
        }
        self.query = query
        self.getchdf

    @property
    def getchdf(self):
        try:
            self.df = pandahouse.read_clickhouse(self.query, connection=self.connection)

        except Exception as err:
            print("\033[31m {}".format(err))
            exit(0)