#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2008       Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
"""Match persons RGD style."""

import sys
import os
from collections import defaultdict
from joblib import load  # ??pickle??
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.soundex import soundex, compare
from gramps.gen.lib import Event, Person
from gramps.gen.utils.db import (get_birth_or_fallback, get_death_or_fallback)
from gramps.gen import datehandler
from features import Features
from ftDatabase import fulltextDatabase
# import cProfile
# pr = cProfile.Profile()

sys.path.insert(0, '/share/work/Gramps/work')  # TMP!!

# -------------------------------------------------------------------------
#
# Gramps modules
#
# -------------------------------------------------------------------------
_ = glocale.translation.sgettext

# -------------------------------------------------------------------------
#
# Fulltextdatabase sqlite3 FTS5
#
# -------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# -------------------------------------------------------------------------
#
# Helper functions
#
# -------------------------------------------------------------------------


def get_name_obj(person):
    if person:
        return person.get_primary_name()
    else:
        return None


def get_surnames(name):
    """Construct a full surname of the surnames"""
    return ' '.join([surn.get_surname().lower() for surn in name.get_surname_list()])


def is_initial(name):
    if len(name) > 2:
        return 0
    elif len(name) == 2:
        if name[0] == name[0].upper() and name[1] == '.':
            return 1
    else:
        return name[0] == name[0].upper()


class Match():
    def __init__(self, db, progress, use_soundex, threshold, algoritm):
        self.db = db
        self.progress = progress
        self.my_map = {}
        self.map = {}
        self.list = []
        self.length = 0
        self.index = 0
        self.use_soundex = use_soundex
        self.threshold = threshold
        self.algoritm = algoritm
        self.ftdb = None
        self.features = Features(self.db)
        self.svmModel = load(os.path.abspath(os.path.dirname(__file__)) + '/modelV3.pkl')
        self.ensembleModel = load(os.path.abspath(os.path.dirname(__file__)) + '/modelV3ensemble.pkl')

    def ancestors_of(self, p1_id, id_list):
        if (not p1_id) or (p1_id in id_list):
            return
        id_list.append(p1_id)
        p1 = self.db.get_person_from_handle(p1_id)
        f1_id = p1.get_main_parents_family_handle()
        if f1_id:
            f1 = self.db.get_family_from_handle(f1_id)
            self.ancestors_of(f1.get_father_handle(), id_list)
            self.ancestors_of(f1.get_mother_handle(), id_list)

    def do_find_matches(self):
        self.progress.set_pass('Start', '?')
        try:
            self.setup_data_structures()
            self.find_potentials(self.threshold)
        except AttributeError as msg:
            # RunDatabaseRepair(str(msg), parent=self.window)
            return

    def get_date_strings(self, person):
        """
        Returns tuple of birth/christening and death/burying date strings.
        """
        birth_event = get_birth_or_fallback(self.db, person)
        if birth_event:
            birth = self.get_event_string(birth_event)
        else:
            birth = ['', '']
        death_event = get_death_or_fallback(self.db, person)
        if death_event:
            death = self.get_event_string(death_event)
        else:
            death = ['', '']
        return (birth, death)

    def get_event_string(self, event):
        """
        Return string for an event label.
        """
        if event:
            date_object = event.get_date_object()
            date = ''
            if (date_object.get_text() or date_object.get_year_valid()):
                date = '%s' % datehandler.get_date(event)
                placeId = event.get_place_handle()
                if not placeId:
                    place_title = ''
                else:
                    place = self.db.get_place_from_handle(placeId)
                    place_title = place.get_title()
                    if not place_title:
                        place_name = place.get_name()
                        place_title = place_name.get_text_data_list()[0]
                return [date, place_title]
        return ['', '']

    def setup_data_structures(self):
        length = self.db.get_number_of_people()

        self.progress.set_pass(_('Pass 1: Building indexes'), length)
        self.ftdb = fulltextDatabase(clean=True)  # remove old and generate new ft database - do we always need to reindex??
        for p1_id in self.db.iter_person_handles():
            self.progress.step()
            p1 = self.db.get_person_from_handle(p1_id)
            # generate index
            event_data = self.get_date_strings(p1)
            birthDate = event_data[0][0]
            birthPlace = event_data[0][1]
            deathDate = event_data[1][0]
            deathPlace = event_data[1][1]
            self.ftdb.index(p1, birthDate, birthPlace, deathDate,
                            deathPlace)  # extracts names, clean text
        self.ftdb.commitIndex()  # generates family index aswell (not done yet)

    def find_potentials(self, threshold):
        self.map = {}
        self.my_map = {}
        pkeys = defaultdict(list) # Used to detect if a potential match comes from the same import
        done = []  # use set?
        persons = defaultdict(list)
        # Find key for latest import
        latest = 0
        for p1key in self.db.iter_person_handles():
            p1 = self.db.get_person_from_handle(p1key)
            for tagHandle in p1.tag_list:
                tag = self.db.get_tag_from_handle(tagHandle).get_name()
                if tag.startswith('Imp2'):
                    dat = int(tag.replace('Imp', ''))
                    if dat >= latest:
                        latest = dat
                        persons[dat].append(p1)
                        pkeys[dat].append(p1key)
            if latest == 0: # No import tags
                persons['NoTag'].append(p1)
        if not persons[latest]: # No import tags
            latest = 'NoTag'
        elif persons['NoTag']:
            print("TAG ERROR - mix of tagged and not tagged")
        # Just test persons from latest import or 'NoTag'
        print('testing latest', latest, len(persons[latest]))
        length = len(persons[latest])
        self.progress.set_pass(_('Pass 2: Calculating potential matches'), length)
        for p1 in persons[latest]:
            self.progress.step()
            p1key = p1.handle
            for hit in self.ftdb.getMatchesForHandle(p1key):
                score = hit['score']
                p2key = hit['grampsHandle']
                if p2key in pkeys[latest]  or (p1key, p2key) in done or (p2key, p1key) in done:
                    continue
                done.append((p1key, p2key))
                done.append((p2key, p1key))
                p2 = self.db.get_person_from_handle(p2key)
                if self.algoritm == 'svm':
                    # pr.enable()
                    features = self.features.getFeatures(p1, p2, score)
                    # pr.disable()
                    score = self.svmModel.predict_proba([features])[0][1]
                elif self.algoritm == 'ensemble':
                    features = self.features.getFeatures(p1, p2, score)
                    score = self.ensembleModel.predict_proba([features])[0][1]
                elif self.algoritm == 'score':  # FIX better way of selecting algoritm
                    chance = self.compare_people(p1, p2) / 6.5  # MAX_CHANCE = 6.5 ??
                    combined_score = score * chance
                    score = combined_score
                else:
                    print("Error algorithm")
                    #FIX
                    break
                if score >= threshold:
                    if p1key in self.my_map:
                        val = self.my_map[p1key]
                        if val[1] < score:
                            self.my_map[p1key] = (p2key, score)
                    else:
                        self.my_map[p1key] = (p2key, score)
                    break
        for (key, val) in self.my_map.items():
            self.map[key] = val
        self.list = sorted(self.map)
        self.length = len(self.list)
        self.progress.close()
        # pr.print_stats(sort='cumtime')

    def compare_people(self, p1, p2):
        # from Gramps find Duplicate

        name1 = p1.get_primary_name()
        name2 = p2.get_primary_name()

        # FIX lower case
        chance = self.name_match(name1, name2)
        if chance == -1:
            return -1

        birth1_ref = p1.get_birth_ref()
        if birth1_ref:
            birth1 = self.db.get_event_from_handle(birth1_ref.ref)
        else:
            birth1 = Event()

        death1_ref = p1.get_death_ref()
        if death1_ref:
            death1 = self.db.get_event_from_handle(death1_ref.ref)
        else:
            death1 = Event()

        birth2_ref = p2.get_birth_ref()
        if birth2_ref:
            birth2 = self.db.get_event_from_handle(birth2_ref.ref)
        else:
            birth2 = Event()

        death2_ref = p2.get_death_ref()
        if death2_ref:
            death2 = self.db.get_event_from_handle(death2_ref.ref)
        else:
            death2 = Event()

        value = self.date_match(birth1.get_date_object(),
                                birth2.get_date_object())
        if value == -1:
            return -1
        chance += value

        value = self.date_match(death1.get_date_object(),
                                death2.get_date_object())
        if value == -1:
            return -1
        chance += value

        value = self.place_match(birth1.get_place_handle(),
                                 birth2.get_place_handle())
        if value == -1:
            return -1
        chance += value

        value = self.place_match(death1.get_place_handle(),
                                 death2.get_place_handle())
        if value == -1:
            return -1
        chance += value

        ancestors = []
        self.ancestors_of(p1.get_handle(), ancestors)
        if p2.get_handle() in ancestors:
            return -1

        ancestors = []
        self.ancestors_of(p2.get_handle(), ancestors)
        if p1.get_handle() in ancestors:
            return -1

        f1_id = p1.get_main_parents_family_handle()
        f2_id = p2.get_main_parents_family_handle()

        if f1_id and f2_id:
            f1 = self.db.get_family_from_handle(f1_id)
            f2 = self.db.get_family_from_handle(f2_id)
            dad1_id = f1.get_father_handle()
            if dad1_id:
                dad1 = get_name_obj(self.db.get_person_from_handle(dad1_id))
            else:
                dad1 = None
            dad2_id = f2.get_father_handle()
            if dad2_id:
                dad2 = get_name_obj(self.db.get_person_from_handle(dad2_id))
            else:
                dad2 = None

            value = self.name_match(dad1, dad2)

            if value == -1:
                return -1

            chance += value

            mom1_id = f1.get_mother_handle()
            if mom1_id:
                mom1 = get_name_obj(self.db.get_person_from_handle(mom1_id))
            else:
                mom1 = None
            mom2_id = f2.get_mother_handle()
            if mom2_id:
                mom2 = get_name_obj(self.db.get_person_from_handle(mom2_id))
            else:
                mom2 = None

            value = self.name_match(mom1, mom2)
            if value == -1:
                return -1

            chance += value

        for f1_id in p1.get_family_handle_list():
            f1 = self.db.get_family_from_handle(f1_id)
            for f2_id in p2.get_family_handle_list():
                f2 = self.db.get_family_from_handle(f2_id)
                if p1.get_gender() == Person.FEMALE:
                    father1_id = f1.get_father_handle()
                    father2_id = f2.get_father_handle()
                    if father1_id and father2_id:
                        if father1_id == father2_id:
                            chance += 1
                        else:
                            father1 = self.db.get_person_from_handle(father1_id)
                            father2 = self.db.get_person_from_handle(father2_id)
                            fname1 = get_name_obj(father1)
                            fname2 = get_name_obj(father2)
                            value = self.name_match(fname1, fname2)
                            if value != -1:
                                chance += value
                else:
                    mother1_id = f1.get_mother_handle()
                    mother2_id = f2.get_mother_handle()
                    if mother1_id and mother2_id:
                        if mother1_id == mother2_id:
                            chance += 1
                        else:
                            mother1 = self.db.get_person_from_handle(mother1_id)
                            mother2 = self.db.get_person_from_handle(mother2_id)
                            mname1 = get_name_obj(mother1)
                            mname2 = get_name_obj(mother2)
                            value = self.name_match(mname1, mname2)
                            if value != -1:
                                chance += value
        return chance

    def date_match(self, date1, date2):
        # FIX so that
        # 1712-12-03 :: 1715-10-02 = -1.0 Different year
        # 0000-00-00 :: 0000-00-00 = 0.0  No data
        # 1685-00-00 :: 1685-00-00 = 0.75 just year
        # 1685-05-00 :: 1685-07-00 = 0.5  different month
        # 1685-09-00 :: 1685-09-00 = 0.87 same month
        # 1685-10-21 :: 1685-10-21 = 1.0  identical

        if date1.is_empty() or date2.is_empty():
            return 0
        if date1.is_compound() or date2.is_compound():
            return self.range_compare(date1, date2)
        if date1.match(date2) and (date1.get_year() == date2.get_year()):
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

    def name_compare(self, s1, s2):
        if self.use_soundex:
            try:
                return compare(s1, s2)
            except UnicodeEncodeError:
                return s1 == s2
        else:
            return s1 == s2

    def name_match(self, name, name1):

        if not name or not name1:
            return 0

        srn1 = get_surnames(name)
        sfx1 = name.get_suffix()
        srn2 = get_surnames(name1)
        sfx2 = name1.get_suffix()

        if not self.name_compare(srn1, srn2):  # What if surnames is a list?
            return -1
        if sfx1 != sfx2:
            if sfx1 != "" and sfx2 != "":
                return -1

        if name.get_first_name().lower() == name1.get_first_name().lower():
            return 1
        else:
            list1 = name.get_first_name().lower().split()
            list2 = name1.get_first_name().lower().split()

            if len(list1) < len(list2):
                return self.list_reduce(list1, list2)
            else:
                return self.list_reduce(list2, list1)

    def place_match(self, p1_id, p2_id):
        if p1_id == p2_id:
            return 1

        if not p1_id:
            name1 = ""
        else:
            p1 = self.db.get_place_from_handle(p1_id)
            name1 = p1.get_title().lower()

        if not p2_id:
            name2 = ""
        else:
            p2 = self.db.get_place_from_handle(p2_id)
            name2 = p2.get_title().lower()

        if not (name1 and name2):
            return 0
        if name1 == name2:
            return 1

        list1 = name1.replace(",", " ").split()
        list2 = name2.replace(",", " ").split()

        value = 0
        for name in list1:
            for name2 in list2:
                if name == name2:
                    value += 0.5
                elif name[0] == name2[0] and self.name_compare(name, name2):
                    value += 0.25
        return min(value, 1) if value else -1

    def list_reduce(self, list1, list2):
        value = 0
        for name in list1:
            for name2 in list2:
                if is_initial(name) and name[0] == name2[0]:
                    value += 0.25
                elif is_initial(name2) and name2[0] == name[0]:
                    value += 0.25
                elif name == name2:
                    value += 0.5
                elif name[0] == name2[0] and self.name_compare(name, name2):
                    value += 0.25
        return min(value, 1) if value else -1
