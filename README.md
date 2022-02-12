# Gramps_Treemerge
A Gramps plugin to merge data from 2 trees

# DESIGN

The implementation borrows a lot from Gramps plugins as GraphView and 'Find Possible Duplicate People'.

  * Generate a text-representation of a person (possibly including parents) with names, dates, places
      and index that in a free-text database
  * Use a person text-representation as a query to the free-text database
  * Test the top X results more detailed for a possible match
  * Use a machine-learning tool like SVM to categorise matches. SVM can give a probability
    that a match is an exact match 

The above design avoids the need to compare all persons to all other persons thus cutting the algorithm complexity from
n-squared to k * n where n is the number of persons in the database and k is an implementation dependent constant.

Matches can be grouped in 3 categories 'certain match', 'maybe', 'certain nomatch' where only 'maybe'
needs to be inspected manually.

A 'certain match' would be where a SVM calculated probability is above 90 - 95 % of being an exact match. 

SVM categorisation is based on 'feature vectors' where features usually range from -1 (complete miss-match) to
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

## TODO/IDEAS

* Use full Graphview to inspect the family-trees around a match
  - Graphview adapted to show 1-2 generations above and below a match including arcs between matched people
  (Now there is a limited version that show 1 generation above and below the match)

  - Using a full Graphview window with the 2 matched persons as center-person(s) would be ideal

* Merge all 'certain match' without user intervention

* Support family-matching and merging

* Experiment with more features

## QUESTIONS

- Is it possible to keep enough information to be able undo a merge in case there is an error discovered later?


## USE

Start Treemerge from the tools menu ('Family Tree Processing' -> 'Merge 2 trees by matching persons')

Press **Match**

Select a matched pair

![Main window](/TreemergeMain.png)

Press **Compare** to see the two family-trees (colored blue and brown) for the matched persons in
the selected pair (colored green).

![Graphical compare of match](/TreemergeCompare.png)

Clicking on a person in the graph will set the active person which
can be usefull if you are using GraphView and want to inspect the families in more detail.

In order to merge the selected matched pair of persons press **Merge**, which will start Gramps normal PersonMerge.
