# balancier
Book balancer


Sorry, due to bad planning I didn't have nearly as much time as I hoped to work on this.
I got to put in just shy of two hours.

This also didn't leave me a ton of time to thoroughly answer the questions, so I apologize
for the brevity below.

Things I would change if I had more time:
* *Tests!* Unit tests everywhere to ensure everything is working like it should.
* Some refactoring.
* More refactoring - separate stuff into individual files
* CSVs don't match. Mine are ordered by ID, the examples are not. Maybe I missed something but
  it seems my are in the correct order.

1. How long did you spend working on the problem? What did you find to be the most difficult part?

About two hours. Hardest part was consistently spelling "likelihood" correctly :). Kidding, understanding 
the requirements was definitely the hardest part. I was confused about 
the relationship between banks and facilities and covenant heirarchy. Had to read the requirements a 
few times to get it.

2. How would you modify your data model or code to account for an eventual introduction of new, 
   as­of­yet unknown types of covenants, beyond just maximum default likelihood and state restrictions?

I believe I structured the classes to allow for that.

3. How would you architect your solution as a production service wherein new facilities can be introduced 
   at arbitrary points in time. Assume these facilities become available by the finance team emailing your 
   team and describing the addition with a new set of CSVs.

I'd create a REST API to add the new facilities, and store everything in a db. 

4. Your solution most likely simulates the streaming process by directly calling a method in your code to 
   process the loans inside of a for loop. What would a REST API look like for this same service? 
   Stakeholders using the API will need, at a minimum, to be able to request a loan be assigned to 
   a facility, and read the funding status of a loan, as well as query the capacities remaining in facilities.

I believe the code is structured to make such a modification fairly simple. Although it would make sense
to store facilities, banks, etc. in a database at this point.

5. How might you improve your assignment algorithm if you were permitted to assign loans in batch rather 
   than streaming? We are not looking for code here, but pseudo code or description of a revised algorithm appreciated.

I would do some sort of grouping based on the restrictions set by covenants. It would be possible to lump
several loans into these groups and mass assign.

6. Because a number of facilities share the same interest rate, it’s possible that there are a number 
   of equally appealing options by the algorithm we recommended you use (assigning to the cheapest facility). 
   How might you tie­break facilities with equal interest rates, with the goal being to maximize the likelihood 
   that future loans streaming in will be assignable to some facility?


