# -*- coding: utf-8 -*-
# This Python file uses the following encoding: utf-8

#!! NEED TO BE ADAPTED TO GRAMPS ENVIRONMENT AND DATABASE !!

import math
from datetime import date

_cache = {}

def cos(l1, l2):
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


def compName(n1, n2):
    """ Compare names: n1 n2 strings, blankspace separated names
        return value between -1 (mismatch) and 1 (match)
        return None if any of n1, n2 is empty
        can be used on names, normalised names
    """
    if (not n1) or (not n2): return None
    nn1 = n1.strip().split()
    nn2 = n2.strip().split()
    if (not nn1) or (not nn2): return None
    if (len(nn1) > len(nn2)):
        return (2.0 * len(set(nn2).intersection(nn1)) - len(nn2)) / float(
            len(nn2))
    else:
        return (2.0 * len(set(nn1).intersection(nn2)) - len(nn1)) / float(
            len(nn1))

def compareName(n1, n2):
    """ Compare names: n1 n2 strings, blankspace separated names
        return value between -1 (mismatch) and 1 (match)
        return None if any of n1, n2 is empty
        can be used on names, normalised names
    """
    (bon, pos, neg, ant) = (0,0,0,0)
    if (not n1) or (not n2):
        return (bon, pos, neg, ant)
    nn1 = n1.strip().split()
    nn2 = n2.strip().split()
    if (not nn1) or (not nn2):
        return (bon, pos, neg, ant)
    if n1 == n2: bon += 1
    if len(nn1)>1 and len(nn2)>1:
        bon += 1
    overlap = len(set(nn2).intersection(nn1))
    ant += 1
    if overlap:
        pos += overlap #Kolla!
    else:
        neg += 1
    return (bon, pos, neg, ant)

def dateSim(date1, date2):
    """
    date1, date2 date-strings of type 19420823
    returns 'closeness' value between -1 (unequal) and +1 (equal)
    """
    if (not date1) or (not date2): return None
    if date1 == date2: return 1.0
    date1 = str(date1)
    date2 = str(date2)
    if (len(date1) == 4) or (len(date2) == 4):
        if date1[0:4] == date2[0:4]: return 1.0
        else: return -1.0
    try:
        dat1 = date(int(date1[0:4]), int(date1[4:6]), int(date1[6:8]))
    except:
        dat1 = date(int(date1[0:4]), int(date1[4:6]), int(date1[6:8]) - 1)
    try:
        dat2 = date(int(date2[0:4]), int(date2[4:6]), int(date2[6:8]))
    except:
        dat2 = date(int(date2[0:4]), int(date2[4:6]), int(date2[6:8]) - 1)

    d = abs((dat1 - dat2).days)
    if d < 30:
        return (1.0 - d / 15.0)
    else:
        return -1.0


def strSim(txt1, txt2):
    """
      String similarity
      returns a value between -1 and +1
    """
    if (not txt1) or (not txt2): return None
    #print 'strSim', txt1, ':', txt2
    import difflib
    s = difflib.SequenceMatcher(None, txt1, txt2).ratio()
    return 2.0 * (s - 0.5)


def eventSim(ev1, ev2):
    boost = 0
    sim = 0.0
    n = 0
    if ev1.get('date', None) and ev2.get('date', None):
        if (ev1['date']['year'] == ev2['date']['year']):
            sim += 1.0
            n += 1
            boost = 1
        else:
            sim += -1.0
            n += 1
        s = dateSim(ev1['date'].get('date', None),
                    ev2['date'].get('date', None))
        if s is not None:
            sim += s
            n += 1
    if ('place' in ev1) and ('place' in ev2):
        if ev1['place'].get('placeId', None) == ev2['place'].get(
                'placeId', -1):  #different defaults: false if both exits
            sim += 1.0
            n += 1
            boost += 1
        else:
            sim += -1.0
            n += 1
        #Non normalized
        s = strSim(ev1['place'].get('placeString', None),
                   ev2['place'].get('placeString', None))
        if s is not None:
            sim += s
            n += 1
    if (boost == 2):
        sim += 1.0
        n += 1
    return (sim, n)


def nodeSim(p1, p2):
    """ Compare 2 nodes (p1 new, p2 master(rgd))
        returns a value between -1 (unequal) and 1 (equal) """
    if (not (p1 and p2)): return 0.0  #?? OK??
    ##?# Cache results?
    global _cache
    key = '%s;%s' % (p1['_id'], p2['_id'])
    if key in _cache: return _cache[key]
    ##?
    sim = 0.0
    n = 0
    boost = 0
    if 'name' in p1 and 'name' in p2:
        s = compName(p1['name'].get('firstNormalized', None),
                     p2['name'].get('firstNormalized', None))
        if s is not None:
            sim += s
            n += 1
            if (s > 0.99): boost = 1
        s = compName(p1['name'].get('lastNormalized', None),
                     p2['name'].get('lastNormalized', None))
        if s is not None:
            sim += s
            n += 1
            if (s > 0.99): boost += 1
        if (boost == 2):
            sim += 1.0
            n += 1
    for ev in ('birth', 'death'):
        if (ev in p1) and (ev in p2):
            (esim, en) = eventSim(p1[ev], p2[ev])
            sim += esim
            n += en
    similarity = 0.0
    if n > 0: similarity = sim / n
    _cache[key] = similarity
    return similarity


def familySim(p1, p2, RGDdb):
    """compares 2 families using nodeSim for each person in base-family
       father, mother, and all siblings plus compare family-event marriage
       returns a value between -1 (unequal) and 1 (equal)
    """
    fam1 = RGDdb.getFamilyId(p1['_id'], 'child')
    fam2 = RGDdb.getFamilyId(p2['_id'], 'child')
    if not (fam1 and fam2): return 0.0
    ##?# Cache results?
    global _cache
    key = '%s;%s' % (fam1, fam2)
    if key in _cache: return _cache[key]
    (husb1, wife1, children1) = RGDdb.getFamilyMembers({'_id': fam1})
    (husb2, wife2, children2) = RGDdb.getFamilyMembers({'_id': fam2})

    sim = 0.0
    n = 0
    if husb1 and husb2:
        sim += nodeSim(husb1, husb2)
        n += 1
    if wife1 and wife2:
        sim += nodeSim(wife1, wife2)
        n += 1

    if len(children1) <= len(children2):
        for child1 in children1:
            max = -2.0
            for child2 in children2:
                cns = nodeSim(child1, child2)
                if cns > max: max = cns
            sim += max
            n += 1
    else:
        for child2 in children2:
            max = -2.0
            for child1 in children1:
                cns = nodeSim(child1, child2)
                if cns > max: max = cns
            sim += max
            n += 1
    """
    #Marriage ??
    if ('marriage' in pFam) and ('marriage' in rgdFam):
        (esim, en) = eventSim(pFam['marriage'], rgdFam['marriage'])
        sim += esim
        n += en
    """
    similarity = 0.0
    if n > 0: similarity = sim / n
    _cache[key] = similarity
    return similarity


def extra(p1, p2, RGDdb):
    """
      Some extra features for SVM classification
       nameSim (normalized first, last)
       birthSim (date, place)
       birthYear
       deathSim
       famSim
    """
    res = {
        'nameSim': 0.0,
        'firstNameSim': 0.0,
        'birth': 0.0,
        'birthYear': 0.0,
        'death': 0.0,
        'deathYear': 0.0,
        'famSim': 0.0
    }
    if (not (p1 and p2)): return res
    if 'name' in p1 and 'name' in p2:
        s = compName(
            p1['name'].get('firstNormalized', '') +
            p1['name'].get('lastNormalized', ''),
            p2['name'].get('firstNormalized', '') +
            p2['name'].get('lastNormalized', ''))
        if s is not None: res['nameSim'] = s
        s = compName(p1['name'].get('firstNormalized', ''),
                     p2['name'].get('firstNormalized', ''))
        if s is not None: res['firstNameSim'] = s
    for ev in ('birth', 'death'):
        if (ev in p1) and (ev in p2):
            (esim, en) = eventSim(p1[ev], p2[ev])
            if en != 0: res[ev] = esim / en
            else: res[ev] = 0.0
            if p1[ev].get('date', None) and p2[ev].get('date', None):
                if (p1[ev]['date']['year'] == p2[ev]['date']['year']):
                    res[ev + 'Year'] = 1.0
    res['famSim'] = familySim(p1, p2, RGDdb)
    return res

def compEvent(ev1, ev2):
    (bonus, pos, neg, ant) = (0,0,0,0)
    if ('date' not in ev1) or ('date' not in ev2):
        return (bonus, pos, neg, ant)
    year1 = 0
    mon1 = 0
    day1 = 0
    year2 = 0
    mon2 = 0
    day2 = 0
    if ev1['date'] and ev2['date']:
        if 'date' in ev1['date'].keys() and 'date' in ev2['date'].keys():
            year1 = int(ev1['date']['year'])
            mon1 = int(ev1['date']['month'])
            day1 = int(ev1['date']['day'])
            year2 = int(ev2['date']['year'])
            mon2 = int(ev2['date']['month'])
            day2 = int(ev2['date']['day'])
            if ev1['date'] == ev2['date']: bonus += 1 #datum
        else:
            year1 = int(ev1['date']['year'])
            year2 = int(ev2['date']['year'])
    if year1==0 or year2==0:
        #print('Year==0', year1, year2)
        pass
    else:
        ant += 1
        if year1 == year2: #year
            bonus += 1
            pos += 1
        else:
            neg += 1
    if mon1 and mon2: #month
        ant += 1
        if mon1 == mon2:
            pos += 1
            if day1 == day2:
                bonus += 1 #month + day
        else: neg += 1
    if abs(year1 - year2) > 10:
        neg += 1 #year +/- 10
    if day1 and day2: #day
        ant += 1
        if day1 == day2:
            pos += 1
        else:
            neg += 1
    try:
        if ev1['place']['placeId'] == ev2['place']['placeId']:
            pos += 1
            try:
                if ev1['date']['date'] == ev2['date']['date']:
                    bonus += 1 #place + date
            except: pass
            if year1 == year2 and year1 > 0:
                bonus += 1 #place + year
        else:
            neg += 1
        ant += 1
    except: pass
    #else test place? FIX ?
    return (bonus, pos, neg, ant)

def familyRelations(p1, p2):
    #One does not belong to a family as child
    p1F = p1.get('famc', None)
    p2F = p2.get('famc', None)
    #both belong to a family as child but different families
    if p1F and p2F:
        if p1F != p2F:
            return (0, 0.5, '?')
        #syskon
        else:
            return (0, 1, '-')
    #Only one belong to a family as child
    elif p1F or p2F:
        return (1, 0, '+')
    return (0, 0, '')

def nodeSimQ(p1, p2):
    """ Compare 2 nodes (p1 new, p2 master(rgd))
        returns a value between -1 (unequal) and 1 (equal) """
    (bonSum, posSum, negSum, antSum) = (0,0,0,0)
    if (not (p1 and p2)):
        return ('', 0)
    if (p1['sex'] and p2['sex']):
        if (p1['sex']!=p2['sex']):
            negSum += 1
    try:
        if ( (int(p1['death']['date']['year']) < int(p2['birth']['date']['year'])) or
             (int(p2['death']['date']['year']) < int(p1['birth']['date']['year'])) ):
            negSum += 2
    except:
        pass
    (bon, pos, neg, ant) = compareName(p1['name']['firstNormalized'], p2['name']['firstNormalized'])
    bonSum += bon
    posSum += pos
    negSum += neg
    antSum += ant
    if negSum>=2: return ('', 0)
    (bon, pos, neg, ant) = compareName(p1['name']['lastNormalized'], p2['name']['lastNormalized'])
    bonSum += bon
    posSum += pos
    negSum += neg / 2.0
    antSum += ant
    if negSum>=2: return ('', 0)
    for ev in ('birth', 'death'):
        if (ev in p1) and (ev in p2):
            (bon, pos, neg, ant) = compEvent(p1[ev], p2[ev])
            bonSum += bon
            posSum += pos
            negSum += neg
            antSum += ant
            if negSum>=2: return ('', 0)
    if posSum<=2 or antSum<=3:
        return ('', 0)
    (bon, neg, qual) = familyRelations(p1, p2)
    bonSum += bon
    negSum += neg
    if bonSum<=2 or posSum<=negSum or negSum>=2:
        return ('', 0)
    if antSum>0 and (float(posSum) / float(antSum) < 0.7):
        return ('', 0)
    totp = bonSum + posSum - (antSum - posSum) - negSum
    if qual == '+':
        totp += 1
    elif qual == '-':
        totp -= 2
    return (qual, totp)

def getFeatures(person1, person2, RGDdb, score=None, profile='std'):
    profiles = {'std': ['score', 'nodeSim', 'cosMatch', 'birth', 'birthYear', 'death', 'deathYear', 'firstNameSim', 'famSim'],
                'dev': [],
                'all': []}

    featureList = profiles[profile]
    (qual, nodeScore) = nodeSimQ(person1, person2)
    similarity = nodeSim(person1, person2)
    features = {'score': score, 'quality': qual, 'nodeScore': nodeScore, 'nodeSim': similarity,
                'cosPerson': cos(person1['personText'], person2['personText']),
                'cosMatch': cos(person1['matchText'], person2['matchText'])}
    features.update(extra(person1, person2, RGDdb))
    #print('Features', features)
    return list(map(lambda x: features[x], featureList))
