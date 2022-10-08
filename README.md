# CRYPT-OR-SWIM
#### Video Demo:  https://youtu.be/odnu_ZXD5gc
#### Description:
This project is intended to create a trading platform for cryptocurrency that also has a social element. It is based on PSET9 Finance, with the main difference of having
to interact with another API. The main difficulty was trying to figure out how to parse the information and reuse some of the code. Also in the way I realized that
the free version of the API had a 1 second request limit, so I had to figure out how to overcome that.

The "helpers.py" file was modified to point to the Nomics API url, using the format described in the Nomics documentation. The response kept showing an error, so I finally
realized that the route had to use an additional route description ("[0]").

There is also a Leaderboard that shows every participant how everyone else is doing, ordered by the value of their portfolio plus cash. This was done via modifying the
"application.py" file, querying the portfolio of all participants, updating the price for all symbols and finally creating a joined query of both available cash
and the current portfolio value for every participant.

The leaderboard HTML file contains simply the result of the query of leaderboard application, ordered by the value of cash plus stocks, thanks to a Jinja function "sort".

In the index file, I added the last 24 hour variation in price, included in the Nomics API service. This is saved as a new column in "portfolio", and similiar to the "price"
variable, it is overwritten every time the index or history pages are queried. The value is stored as a percentage (1 to 100) number. The index.html page formats the percentage
conditionally, if it is over zero the text is green and else it is red. It also adds a "%" sign at the end of the queried number.

I decided on creating an auxiliary database that fetched information from the API in the background every time a function in application.py started,
and that the application queried that database,and that way not to have limitations and have less delay. For that I defined a function in application.py that is called
from other sections. This function queries the API and saves the result on a different database. That database in turn stores all variables together with a timestamp,
and the functions like "index" query that auxiliary database with the most recent information (per the timestamp).

I thought about and looked into threading in python. That way I thought of querying the API constantly in the background, and not only when another function
started. The concepto itself is really interesting, but it involved changing every function to explicitly start on its own thread. It also required to create
a different database, as if that background process constatly was writting to a database, when another function would write in that same database it would not be able (for
example when using the "buy" function). I think that if this application would need to scale and be usable by a large number of users, that would be an interesting
aproach to solving speed of use.
In the end, this approach in practice just speeds up the results, as it only needs to query the API once, versus querying the API (with a 1 second limit per query) for every
crypto.