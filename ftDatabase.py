# -*- coding: utf-8 -*-
"""API for fulltext index and search with whoosh"""

import os.path
import re
from whoosh.fields import Schema, ID, KEYWORD
from whoosh import index
from whoosh import qparser
# from whoosh import scoring


class fulltextDatabase():
    def __init__(self, clean=False, writer=True):
        schema = Schema(grampsHandle=ID(stored=True), sex=KEYWORD(
            stored=True), person=KEYWORD(stored=True, lowercase=True))
        directory = os.path.abspath(os.path.dirname(__file__)) + '/ftindex'
        if not os.path.exists(directory):
            os.mkdir(directory)
        if not clean and index.exists_in(directory):
            self.ix = index.open_dir(directory)
        else:
            self.ix = index.create_in(directory, schema)
        if writer:
            self.writer = self.ix.writer()
        self.parser = qparser.QueryParser('person', schema=schema, group=qparser.OrGroup)

    def cleanText(self, text):
        # lower case
        # ersätta alla icke-bokstäver med blanktecken
        text = re.sub('[^\s\w]|\d|_', ' ', text.lower())  # FIXME
        return text

    def addDocument(self, grampsHandle, text, sex=''):
        self.writer.add_document(grampsHandle=grampsHandle, sex=sex, person=text)

    def index(self, person, birthDate, birthPlace, deathDate, deathPlace):
        """Generate fulltext from person-record"""
        text = []
        name = person.get_primary_name()
        text.append(self.cleanText(name.get_first_name()))
        for surn in name.get_surname_list():
            text.append("LN" + self.cleanText(surn.get_surname()))
        if birthDate:
            text.append("B" + birthDate)
        if deathDate:
            text.append("D" + deathDate)
        if birthPlace:
            text.append("B" + self.cleanText(birthPlace.replace(' ', '')))
        if deathPlace:
            text.append("D" + self.cleanText(deathPlace.replace(' ', '')))
        # TODO normalize place
        self.addDocument(person.handle, ' '.join(text), sex="gender%s" % str(person.get_gender()))

    def commitIndex(self):
        self.writer.commit()
        # Split on 2 dbs - person and family
        # generate family database here
        # get_all_handles
        #   find father and mother
        #   person.get_main_parents_family_handle()
        #     db.get_family_from_handle
        #     family.get_father_handle
        #     family.get_mother_handle
        #   gen familyText, index
        # commit familyText db

    def getMatchesForHandle(self, handle, ant=5):
        with self.ix.searcher() as searcher:
            res = searcher.document(grampsHandle=handle)
            q = self.parser.parse("sex:%s AND (%s)" % (res['sex'], res['person']))
            res = searcher.search(q, limit=ant, terms=False)
            hits = []
            maxScore = 0.0
            for r in res:
                if r.score > maxScore:
                    maxScore = r.score
                if r['grampsHandle'] == handle:
                    continue
                # FIX a global maxScore
                hits.append({'grampsHandle': r['grampsHandle'], 'score': r.score / maxScore})
            return hits
