# -*- coding: utf-8 -*-
"""API for fulltext index and search with Sqlite"""

import os.path
import re
import sqlite3

class fulltextDatabase():
    def __init__(self, clean=False, writer=True):
        directory = os.path.abspath(os.path.dirname(__file__)) + '/ftindex'
        if not os.path.exists(directory):
            os.mkdir(directory)
        databaseFile = directory + "/sqlite.db"  #os.join??
        if clean and os.path.isfile(databaseFile):
            os.remove(databaseFile)
        self.db = sqlite3.connect(databaseFile, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES,
                                  check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.cur = self.db.cursor()
        if clean:
            self.createTables()
        
    def __del__(self):
        self.db.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.close()

    def createTables(self):
        #schema = "grampsHandle, sex, person"
        self.cur.execute("CREATE VIRTUAL TABLE ft USING fts5(grampsHandle, sex, person)")
        self.db.commit()

    def cleanText(self, text):
        # lower case
        # ersätta alla icke-bokstäver med blanktecken
        text = re.sub('[^\s\w]|\d|_', ' ', text.lower())  # FIXME
        return text.strip()

    def cleanDate(self, datestring):
        return re.sub(r'[^\d]', '', datestring)  # remove all non-digits?
    
    def addDocument(self, grampsHandle, text, sex=''):
        self.cur.execute("INSERT INTO ft VALUEs (?, ?, ?)", (grampsHandle, sex, text))
 
    def index(self, person, birthDate, birthPlace, deathDate, deathPlace):
        """Generate fulltext from person-record"""
        text = []
        name = person.get_primary_name()
        text.append(self.cleanText(name.get_first_name()))
        for surn in name.get_surname_list():
            text.append("LN" + self.cleanText(surn.get_surname()))
        #FIX dateyears in addion to full date
        if birthDate:
            bDate = birthDate.replace('-', '') #  use cleanDate?
            text.append("B" + bDate)
            if len(bDate) > 5:
                text.append("B" + bDate[0:4])
        if deathDate:
            dDate = deathDate.replace('-', '') #  use cleanDate
            text.append("D" + dDate)
            if len(dDate) > 5:
                text.append("D" + dDate[0:4])
        if birthPlace:
            text.append("B" + self.cleanText(birthPlace.replace(' ', '')))  # Place as one word
        if deathPlace:
            text.append("D" + self.cleanText(deathPlace.replace(' ', '')))  # Place as one word
        # TODO normalize place
        self.addDocument(person.handle, ' '.join(text), sex="gender%s" % str(person.get_gender()))

    def commitIndex(self):
        self.db.commit()

    def getMatchesForHandle(self, handle, ant=5):
        result = "%s\n" % (handle)  #TMP
        self.cur.execute("SELECT grampsHandle, sex, person FROM ft WHERE grampsHandle='%s'" % handle)
        for row in self.cur:
            #  Use OR propability search
            person = ' OR '.join('"{0}"'.format(w) for w in row['person'].split())
            sex = row['sex']
        sql = "SELECT grampsHandle,person,rank FROM ft WHERE person MATCH '%s' AND sex='%s' ORDER BY RANK LIMIT %d" % (person, sex, ant)
        self.cur.execute(sql)
        hits = []
        maxScore = 0.0
        for row in self.cur:
            score = - row['rank']
            if score > maxScore:
                maxScore = score
            if (score / maxScore) < 0.5:
                break
            #result += "%s, %s, %s, %s\n" % (row['grampsHandle'], row['person'], str(score), str(maxScore))
            result += "%s, %s\n" % (row['grampsHandle'], row['person'])
            if row['grampsHandle'] == handle:
                continue
            # FIX a global maxScore
            hits.append({'grampsHandle': row['grampsHandle'], 'score': score / maxScore})
        with open(os.path.abspath(os.path.dirname(__file__)) + '/ftindex/sqlite.txt', 'a') as f:
            f.write(result)
            f.write("--\n")
        return hits
