""" Perform caching operations """
from sqlite3 import connect
from os import path
from json import load
from glob import glob
from requests import Request
from requests_cache import CachedSession
from solvers import GoogleAnswerWordsSolver, GoogleResultsCountSolver


class Cache:
    """ Cache class for operating on the local SQLite cache """

    def __init__(self):
        self.session = CachedSession('db/cache', allowable_codes=(200, 302, 304))
        self.solvers = [
            GoogleAnswerWordsSolver(),
            GoogleResultsCountSolver()
        ]

    def prune(self):
        """ Prune stale entries from the local cache """
        urls = []
        for solver in self.solvers:
            for filename in sorted(glob('games/*.json')):
                game = load(open(filename))
                for turn in game.get('questions'):
                    urls.extend(solver.build_urls(turn.get('question'), turn.get('answers')).values())
        stale_entries = []
        for key, (resp, _) in self.session.cache.responses.items():
            if resp.url not in urls and not any(step.url in urls for step in resp.history):
                stale_entries.append((key, resp))
        print('Found %s/%s stale entries' % (len(stale_entries), len(self.session.cache.responses.keys())))
        for key, resp in stale_entries:
            print('Deleting stale entry: %s' % resp.url)
            self.session.cache.delete(key)

    def refresh(self):
        """ Refresh the local cache with unsaved questions """
        urls = []
        for solver in self.solvers:
            for filename in sorted(glob('games/*.json')):
                game = load(open(filename))
                for turn in game.get('questions'):
                    urls.extend(solver.build_urls(turn.get('question'), turn.get('answers')).values())
        cache_misses = [
            url for url in urls if not self.session.cache.create_key(
                self.session.prepare_request(Request('GET', url))
            ) in self.session.cache.responses
        ]
        print('Found %s/%s URLs not in cache' % (len(cache_misses), len(urls)))
        for idx, url in enumerate(cache_misses):
            print('Adding cached entry: %s' % url)
            response = self.session.get(url)
            if '/sorry/index?continue=' in response.url:
                exit('ERROR: Google rate limiting detected. Cached %s pages.' % idx)

    @staticmethod
    def vacuum():
        """ Perform an SQL vacuum on the local cache to save space """
        conn = connect("db/cache.sqlite")
        conn.execute("VACUUM")
        conn.close()

    @staticmethod
    def import_sql():
        """ Import saved SQL dumps into a local SQLite cache """
        conn = connect("db/cache.sqlite")
        for filename in sorted(glob('db/*.sql')):
            print('Importing SQL %s' % filename)
            sql = open(filename, 'r').read()
            cur = conn.cursor()
            cur.executescript(sql)
        conn.close()

    def export(self):
        """ Export the local cache to SQL dump files """
        for filename in sorted(glob('games/*.json')):
            game = load(open(filename))
            show_id = path.basename(filename).split('.')[0]
            if not path.isfile('./db/%s.sql' % show_id):
                print('Exporting SQL %s' % show_id)
                urls = []
                for solver in self.solvers:
                    for turn in game.get('questions'):
                        urls.extend(solver.build_urls(turn.get('question'), turn.get('answers')).values())
                url_keys = [self.session.cache.create_key(
                    self.session.prepare_request(Request('GET', url))
                ) for url in urls]
                conn = connect(':memory:')
                cur = conn.cursor()
                cur.execute("attach database 'db/cache.sqlite' as cache")
                cur.execute("select sql from cache.sqlite_master where type='table' and name='urls'")
                cur.execute(cur.fetchone()[0])
                cur.execute("select sql from cache.sqlite_master where type='table' and name='responses'")
                cur.execute(cur.fetchone()[0])
                for key in list(set(url_keys)):
                    cur.execute("insert into urls select * from cache.urls where key = '%s'" % key)
                    cur.execute("insert into responses select * from cache.responses where key = '%s'" % key)
                conn.commit()
                cur.execute("detach database cache")
                with open('db/%s.sql' % show_id, 'w') as file:
                    for line in conn.iterdump():
                        file.write('%s\n' % line.replace(
                            'TABLE', 'TABLE IF NOT EXISTS'
                        ).replace(
                            'INSERT', 'INSERT OR IGNORE'
                        ))
                conn.close()
