# Freqwatch v0.1
Joshua Davis (freqwatch -!- covert.codes)  
http://covert.codes/freqwatch/


Updates in v0.2
===============

* Client ID goes to database
* Experimental GPS (not finished yet, need help testing)


Introduction
============

* Explore vast regions of the RF spectrum

* Log radio activity to a mysql database for trend analysis

* Delegate scanners to find radio traffic and log it

* Delegate monitors to store interesting data in the database


Usage
=====

* Install (see the INSTALL file)

* Use the 'blacklist' file to prevent frequency ranges from showing up in
  your database / output

* Configure some sticks as scanners using freqwatch.conf.  Scanners scan
  frequency ranges and log signals above a defined threshold to the database,
  in the 'freqs' table.

* Configure other sticks as monitors by using the modified rtl_fm included.
  Use regular rtl_fm options to specify frequency ranges (several to scan
  different frequencies), etc.  The output will be logged to the database
  'intercepts' table.

* See the freqwatch.conf file for examples

* Use the intercept.py file in the rtl_fm_new directory to pull data from
  the monitor database.  The monitor system still has problems (inserts
  blanks in the output...)


Useful Commands
===============

* Get rtl_fm_new data to listen to / decode: mysql --binary-mode -e "select group_concat(data separator '') from intercepts order by date, time;" -A -B -r -L -N freqwatch -u freqwatch -p > output

* Or better yet, use intercept.py in the rtl_fm directory

* Intercept WBFM: rtl_fm -f 95.7e6 -s 170k -A fast -r 32k -l 0 | play -r 32k -t raw -e s -b 16 -c 1 -V1 - (they suggest using -E deemp, but that doesn't work for me)

* Listen to WBFM on the command line: cat file | play -t raw -r 32k -e signed-integer -b 16 -c 1 -V1 -


Security Note
==============

You should run freqwatch in a controlled environment (e.g. with the web and
database servers on localhost, and a firewall blocking the relevant ports
from outsiders.)


Bugs
====

Please send bugs to freqwatch -!- covert.codes

