# -*- coding: utf-8 -*-

# Note: As pointed out in the text, there are now additional/better ways to process retweets
# as the Twitter API has evolved. In particular, take a look at the retweet_count field of the
# status object. See https://dev.twitter.com/docs/platform-objects/tweets. However, the technique
# illustrated in this code is still relevant as some Twitter clients may not follow best practices
# and still use the "RT" or "via" conventions to tweet as opposed to using the Twitter API to issue
# a retweet.

import sys
import couchdb
from couchdb.design import ViewDefinition
from prettytable import PrettyTable

DB = sys.argv[1]

try:
    server = couchdb.Server('http://localhost:5984')
    db = server[DB]
except couchdb.http.ResourceNotFound, e:
    print """CouchDB database '%s' not found. 
Please check that the database exists and try again.""" % DB
    sys.exit(1)

if len(sys.argv) > 2 and sys.argv[2].isdigit():
    FREQ_THRESHOLD = int(sys.argv[2])
else:
    FREQ_THRESHOLD = 3

# Map entities in tweets to the docs that they appear in

def entityCountMapper(doc):
    if doc.get('text'):
        import re
        m = re.search(r"(RT|via)((?:\b\W*@\w+)+)", doc['text'])
        if m:
            entities = m.groups()[1].split()
            for entity in entities:
                yield (entity.lower(), [doc['_id'], doc['id']])
        else:
            yield ('@', [doc['_id'], doc['id']])


def summingReducer(keys, values, rereduce):
    if rereduce:
        return sum(values)
    else:
        return len(values)


view = ViewDefinition('index', 'retweet_entity_count_by_doc', entityCountMapper,
                      reduce_fun=summingReducer, language='python')
view.sync(db)

# Sorting by value in the client is cheap and easy
# if you're dealing with hundreds or low thousands of tweets

entities_freqs = sorted([(row.key, row.value) for row in
                        db.view('index/retweet_entity_count_by_doc',
                        group=True)], key=lambda x: x[1], reverse=True)

field_names = ['Entity', 'Count']
pt = PrettyTable(field_names=field_names)
pt.align = 'l'

for (entity, freq) in entities_freqs:
    if freq > FREQ_THRESHOLD and entity != '@':
        pt.add_row([entity, freq])

print pt
