# Gramps_Treemerge
A Gramps plugin to match (detect overlap) and merge data from 2 trees

# DESIGN

The implementation borrows a lot from Gramps plugins as GraphView and 'Find Possible Duplicate People'.

  * Generate a text-representation of a person (possibly including parents) with names, dates, places
      and index that in a free-text database
  * Use a person text-representation as a query to the free-text database
  * Test the top X results more detailed for a possible match
  * Use a machine-learning tool like SVM or ensemble classification to categorise matches.
    They are machine-learning tools that you
    train to recognize and group objects (feature vectors) into categories.
    In this case feature vectors are comparisons between persons and categories are 'match' and 'no match'.
    A feature vector consists of various aspect like name similarity, event similarity, see below.
    The classification give a probability that a match is an exact match 

The above design avoids the need to compare all persons to all other persons thus cutting the algorithm complexity from
n-squared to k * n where n is the number of persons in the database and k is an implementation dependent constant.

Matches can be grouped in 3 categories 'certain match', 'maybe', 'certain nomatch' where only 'maybe'
needs to be inspected manually.

A 'certain match' would be where a calculated probability is above 90 - 95 % of being an exact match. 

Categorisation is based on 'feature vectors' where features usually range from -1 (complete miss-match) to
1 (complete match). Features used are:
  * _score_, How good a hit from the free-text database is
  * _personSim_, Similarity of persons based on name and event-date comparisons
  * _familySim_, Mean of similarity for father and mother
  * _birthSim_, Similarity of birth-date and birth-place
  * _birthYearSim_, Birth years equal
  * _deathSim_, Similarity of death-date and death-place
  * _deathYearSim_, Death years equal
  * _firstNameSim_, Name equality
  * _firstNameStrSim_, String similarity of all names sorted and concatenated in a string
  * _lastNameSim_, Name equality
  * _compareLifeSpans_, Lifespans compatible

**[SVM](https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVC.html)**  uses only the above features.

**[Ensemble](https://scikit-learn.org/stable/modules/ensemble.html#stacking)** combines a number of diffrent categorizers
for better accuracy.

## TODO/IDEAS

* Use full Graphview to inspect the family-trees around a match
  - Graphview adapted to show 1-2 generations above and below a match including arcs between matched people
  (Now there is a limited version that show 1 generation above and below the match)

  - Using a full Graphview window with the 2 matched persons as center-person(s) would be ideal

* Support family-matching and merging

* Experiment with more features

## QUESTIONS

- Is it possible to keep enough information to be able undo a merge in case there is an error discovered later?


## USE
**Warning: Data Corruption Risk**

Mass changes mean more potential for mangling the data. Back up your current tree **BEFORE** using this tool to merge.
If something goes wrong, you will have a way to go back and start over. Make a Gramps XML backup. 

Start Treemerge from the tools menu ('Family Tree Processing' -> 'Merge 2 trees by matching persons')

Possibly select matching algoritm either 'SVM' or 'Ensemble' for a machine learning based classification matching or
'score' which is similar to Gramps score-based matching. Soundex is only used in 'score'-matching.

('score' is the fastest but has least accuracy. 'SVM' is slower but has better accuracy. 'Ensemble' is the slowest algoritm
but also the method with best accuracy.)

Press **Match**

Select a matched pair

![Main window](/TreemergeMain.png)

Press **Compare** to see the two family-trees (colored blue and brown) for the matched persons in
the selected pair (colored green). Dashed lines connect matched persons, color indicate rating
(from green=1.0 via yellow to red=0.5).

The **NOT Match** button will simply remove the selected match from the list.

![Graphical compare of match](/TreemergeCompare.png)

Clicking on a person in the graph will set the active person which
can be usefull if you are using GraphView and want to inspect the families in more detail.

In order to merge the selected matched pair of persons press **Merge**, which will start Gramps normal PersonMerge.

If **Automerge** is pressed all matched pairs with a rating above the selected **Automerge cutoff** will be merged.