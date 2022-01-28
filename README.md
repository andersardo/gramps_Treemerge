# gramps_Treemerge
A gramps plugin to merge data from 2 trees

DESIGN

  * Generate a text-representation of a person (possibly including parents) with names, dates, places
      and index that in a free-text database
  * Use a person text-representation as a query to the free-text database
  * Test the top X results more detailed for a possible match

The above design avoids the need to compare all persons to all other persons thus cutting the algorithm complexity from
n-squared to X * n.

Matches can be grouped in 3 categories 'certain match', 'maybe', 'certain nomatch' where only 'maybe'
needs to be inspected manually.

IDEAS/TODO

Graphview adapted to show 1-2 generations above and below a match including arcs between matched people
alternative
2 Graphview windows with the 2 matched persons as center-person

How to signal to gramps that I want a view with a specific person as center-person

Merge all 'certain match' without user intervention

Is it possible to keep enough information to be able undo a merge in case there is an error?
