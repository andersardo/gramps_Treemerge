# -*- coding: utf-8 -*-
# This Python file uses the following encoding: utf-8

import math
import difflib
import json  #TMP!! FIX
_cache = {}

def cos(l1, l2): #NOT USED
    """
    Similarity between two vectors = cosine for the angle between the vectors:
    cosine  = ( V1 * V2 ) / ||V1|| x ||V2||
    Vectors expressed as strings, split on blankspace, assume boolean weights
    """
    v1 = l1.split()
    v2 = l2.split()
    s = 0
    for w1 in v1:
        if w1 in v2: s += 1
    return s / (math.sqrt(len(v1)) * math.sqrt(len(v2)))

class Features(): # Evt move to Match?
    # For Gramps data
    def __init__(self, db):
        self.db = db
        #cache of personFeatures with key (handle1, handle2)
        self.cache = {}
        self.featureList = ['score', 'personSim', 'birthSim', 'birthYearSim', 'deathSim', 'deathYearSim',
                            'firstNameSim', 'lastNameSim', 'familySim', 'firstNameStrSim',
                            'compareLifespans']
                            #'ParentChild', 'commonFamily']

    def get_names(self, name):
        """
           name: name-object
           return: tuple of strings (first, last)
        """
        return (name.get_first_name().lower(), name.get_surname().lower())

    def nameSim(self, n1, n2):
        """ Compare names: n1 n2 strings, blankspace separated names
            return value between -1 (mismatch) and 1 (match)
            return 0 if any of n1, n2 is empty
            can be used on names, normalised names
        """
        if (not n1) or (not n2): return 0
        nn1 = n1.strip().split()
        nn2 = n2.strip().split()
        if (not nn1) or (not nn2): return 0
        if (len(nn1) > len(nn2)):
            return (2.0 * len(set(nn2).intersection(nn1)) - len(nn2)) / float(
                len(nn2))
        else:
            return (2.0 * len(set(nn1).intersection(nn2)) - len(nn1)) / float(
                len(nn1))

    def nameStrSim(self, n1, n2):  #NOT USED??
        """ Compare names: n1 n2 strings, blankspace separated names
            return value between -1 (mismatch) and 1 (match)
            return 0 if any of n1, n2 is empty
            can be used on names, normalised names
        """
        if (not n1) or (not n2): return 0
        nn1 = n1.strip().split()
        nn2 = n2.strip().split()
        if (not nn1) or (not nn2): return 0
        overlap = set(nn2).intersection(nn1)
        rest1 = ''.join(sort(list(set(nn1).difference(overlap))))
        rest2 = ''.join(sort(list(set(nn2).difference(overlap))))
        s = difflib.SequenceMatcher(None, rest1, rest2).ratio()
        sim = (len(overlap) + s) / (len(overlap) + 1.0)
        return 2.0 * (sim -0.5)
    
    def strSim(self, txt1, txt2):
        """
          String similarity
          txt1, txt2 are strings
          returns a value between -1 and +1
        """
        if (not txt1) or (not txt2): return 0
        s = difflib.SequenceMatcher(None, txt1, txt2).ratio()
        return 2.0 * (s - 0.5)

    def dateSim(self, date1, date2):
        """
        date1, date2: Gramps date-objects
        returns date similarity between -1 and 1
         1712-12-03 :: 1715-10-02 = -1.0 Different years
         0000-00-00 :: 0000-00-00 = 0.0  No data
         1685-00-00 :: 1685-00-00 = 0.75 just year no month
         1685-05-00 :: 1685-07-00 = 0.5  different months
         1685-09-00 :: 1685-09-00 = 0.87 same month
         1685-10-21 :: 1685-10-21 = 1.0  identical
        """
        if date1.is_empty() or date2.is_empty():
            return 0
        if date1.is_compound() or date2.is_compound():
            return self.range_compare(date1, date2)
        if date1.match(date2) and ( date1.get_year() == date2.get_year() ):
            if not date1.get_month_valid() or not date2.get_month_valid():
                return 0.75
            if date1.get_month() == date2.get_month():
                if (date1.get_day() == date2.get_day()) and date1.get_day_valid() and date2.get_day_valid():
                    return 1.0
                else:
                    return 0.87
            else:
                return 0.75
        else:
            return -1

    def range_compare(self, date1, date2):
        """
        called from dateSim
        date1, date2: Gramps compound date-objects
        returns date similarity between -1 and 1
        """
        start_date_1 = date1.get_start_date()[0:3]
        start_date_2 = date2.get_start_date()[0:3]
        stop_date_1 = date1.get_stop_date()[0:3]
        stop_date_2 = date2.get_stop_date()[0:3]
        if date1.is_compound() and date2.is_compound():
            if (start_date_2 <= start_date_1 <= stop_date_2 or
                start_date_1 <= start_date_2 <= stop_date_1 or
                start_date_2 <= stop_date_1 <= stop_date_2 or
                start_date_1 <= stop_date_2 <= stop_date_1):
                return 0.5
            else:
                return -1
        elif date2.is_compound():
            if start_date_2 <= start_date_1 <= stop_date_2:
                return 0.5
            else:
                return -1
        else:
            if start_date_1 <= start_date_2 <= stop_date_1:
                return 0.5
            else:
                return -1

    def placeSim(self, place1, place2):
        """
          place1, place2: Gramps place-handles
          returns string similarity between -1 and 1
        """
        if not place1 or not place2:
            return 0
        placestring1 = self.db.get_place_from_handle(place1).get_title().lower()
        placestring2 = self.db.get_place_from_handle(place2).get_title().lower()
        return self.strSim(placestring1, placestring2)

    def getEvents(self, person):
        """
          person: Gramps person object
          return a dict with (birth, death) event objects
        """
        from gramps.gen.lib import Event

        birth_ref = person.get_birth_ref()
        if birth_ref:
            birth = self.db.get_event_from_handle(birth_ref.ref)
        else:
            birth = Event()

        death_ref = person.get_death_ref()
        if death_ref:
            death = self.db.get_event_from_handle(death_ref.ref)
        else:
            death = Event()
        return {'birth': birth, 'death': death}

    #Possibly test marriage dates aswell??
    
    def eventSim(self, ev1, ev2):
        if ev1.is_empty() or ev2.is_empty():
            return 0        
        return (self.dateSim(ev1.get_date_object(), ev2.get_date_object()) +
                self.placeSim(ev1.get_place_handle(), ev2.get_place_handle())) / 2.0

    def eventYearSim(self, ev1, ev2):
        date1 = ev1.get_date_object()
        date2 = ev2.get_date_object()
        if date1.is_empty() or date2.is_empty() or date1.is_compound() or date2.is_compound():
            return 0
        elif date1.match(date2) and ( date1.get_year() == date2.get_year() ):
            return 1
        #evt ??
        #elif abs(date1.get_year() - date2.get_year()) <= 1:
        #    return 0.25
        else:
            return -1

    def compareLifespans(self, events1, events2):
        """
           events1, events2: dict with events for birth and death
           Test if one born after other is dead
                   or born more than 110 years (max age?) earlier than other
        """
        birth1 = events1['birth']
        death2 = events2['death']
        if (birth1.is_empty() or death2.is_empty()) :
            pass
        else:
            birth1Year = birth1.get_date_object().get_year()
            death2Year = death2.get_date_object().get_year()
            if birth1Year > death2Year:
                return -1.0
            elif death2Year - birth1Year > 110: 
                return -1.0
        birth2 = events1['birth']
        death1 = events2['death']
        if (birth2.is_empty() or death1.is_empty()) :
            pass
        else:
            birth2Year = birth2.get_date_object().get_year()
            death1Year = death1.get_date_object().get_year()
            if birth2Year > death1Year:
                return -1.0
            elif death1Year - birth2Year > 110:
                return -1.0
        return 1.0

    def ParentChild(self, person1, person2):
        """
           Test if there is a parent - child relation between persons
        """
        pass

    def CommonFamily(self, person1, person2):
        """
           Test if there already is a match in familes (parents or children) of the matched pair
        """
        pass
    
    def familySim(self, person1, person2):
        """
          person1, person2: Gramps Person objects
          similarity: between person1 and person2
          return: similarity of family (person and its parents)
        """
        #Think about caching personSim in some way?
        fam1_handle = person1.get_main_parents_family_handle()
        fam2_handle = person2.get_main_parents_family_handle()
        if not fam1_handle or not fam2_handle:
            return 0
        fam1 = self.db.get_family_from_handle(fam1_handle)
        fam2 = self.db.get_family_from_handle(fam2_handle)
        father1_handle = fam1.get_father_handle()
        father2_handle = fam2.get_father_handle()
        mother1_handle = fam1.get_mother_handle()
        mother2_handle = fam2.get_mother_handle()
        similarity = 0
        n = 0
        if father1_handle and father2_handle:
            sim = self.getPersonFeatures(self.db.get_person_from_handle(father1_handle),
                                         self.db.get_person_from_handle(father2_handle))['personSim']
            similarity += sim
            n += 1
        if mother1_handle and mother2_handle:
            sim = self.getPersonFeatures(self.db.get_person_from_handle(mother1_handle),
                                         self.db.get_person_from_handle(mother2_handle))['personSim']
            similarity += sim
            n += 1
        # Think about complementing with childSim in some way.
        if n > 0:
            return float(similarity / n)
        else:
            return 0

    def getPersonFeatures(self, person1, person2):
        """
          person1, person2: Gramps Person objects
          return a dict with features (-1, 1) for
              [personSim, firstNameSim, lastNameSim, birthSim, birthYearSim, deathSim, deathYearSim] 
        """
        try:
            return self.cache[(person1.handle, person2.handle)]
        except:
            pass
        feature = {}
        (first1, last1) = self.get_names(person1.get_primary_name())
        (first2, last2) = self.get_names(person2.get_primary_name())
        feature['firstNameSim'] = self.nameSim(first1, first2)
        feature['firstNameStrSim'] = self.strSim(first1, first2)
        feature['lastNameSim'] = self.nameSim(last1, last2) #self.nameStrSim(last1, last2) #
        events1 = self.getEvents(person1)
        events2 = self.getEvents(person2)
        feature['birthSim'] = self.eventSim(events1['birth'], events2['birth'])
        feature['deathSim'] = self.eventSim(events1['death'], events2['death'])
        feature['birthYearSim'] = self.eventYearSim(events1['birth'], events2['birth'])
        feature['deathYearSim'] = self.eventYearSim(events1['death'], events2['death'])
        #Compare lifespans (p2 död mer 100 år sennare än p1 född eller död före född)
        if 'compareLifespans' in self.featureList:
            feature['compareLifespans'] = self.compareLifespans(events1, events2)
        if 'ParentChild' in self.featureList:
            feature['ParentChild'] = self.ParentChild(person1, person2)
        if 'CommonFamily' in self.featureList:
            feature['CommonFamily'] = self.CommonFamily(person1, person2)
        boost = 0
        n = 0
        if feature['firstNameSim'] > 0.9:
            boost = 1
            n = 1
        if feature['lastNameSim'] > 0.9:
            boost += 1
            n += 1
        if feature['birthSim'] > 0.9:
            boost += 1
            n += 1
        if feature['deathSim'] > 0.9:
            boost += 1
            n += 1
        feature['personSim'] = (feature['firstNameSim'] + feature['lastNameSim'] +
                                feature['birthSim'] + feature['deathSim'] + boost) / (4.0 + n)
        self.cache[(person1.handle, person2.handle)] = feature
        self.cache[(person2.handle, person1.handle)] = feature
        return feature
    
    def getFeatures(self, person1, person2, score=0):
        """
          person1, person2: Gramps Person objects
          score: score from freetext-search normalised
          return a dict/vector with features (-1, 1) for
              [score, personSim, firstNameSim, lastNameSim, birthSim, birthYearSim, deathSim, deathYearSim, familySim] 
        """
        feature = self.getPersonFeatures(person1, person2)
        feature['score'] = score
        feature['familySim'] = self.familySim(person1, person2)
        #log = (person1.gramps_id, person2.gramps_id, self.get_names(person1.get_primary_name()), self.get_names(person2.get_primary_name()), feature)
        #print(json.dumps(log))
        return list(map(lambda x: feature[x], self.featureList))

