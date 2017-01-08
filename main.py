#!/usr/bin/env python3

from __future__ import print_function
from __future__ import division

import string, itertools, logging, datetime, traceback
from dccourts_scraper import DCCourtsScraper, ScraperException

file_handler = logging.FileHandler("scraper.log", mode='w')
file_handler.setLevel(logging.DEBUG)
errorfile_handler = logging.FileHandler("errors.log", mode='w')
errorfile_handler.setLevel(logging.WARN)
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s %(asctime)s %(message)s',
                    handlers=[logging.StreamHandler(),
                              file_handler,
                              errorfile_handler])
logging.getLogger('requests').setLevel(logging.WARN)

import pymongo
client = pymongo.MongoClient()
db = client.dccourts

db.drop_collection('cases')
db.drop_collection('history')

from blessings import Terminal
t = Terminal()

def main():

    # TODO: ScraperException should have subtypes
    # TODO: should warnings go into history log as well
    # TODO: ensure sum of num_results in history log corresponds with number of cases in database
    # TODO: be able to run a single search query at once
    # TODO: if search query is too broad, either return error or internally handle using smaller
    #       subqueries
    # TODO: use db to check if a query is completely done and prevent doing it again!! (important)
    # TODO: time how long each initial search query takes, how long getting the whole query (multiple pages takes),
    #       and how long the whole process takes
    # TODO: set up process to rerun the entire scrape on a weekly basis without deleting any data or running into any issues
    #       this may require two modes - "update" which ignores if things are already done, and "continue" ?
    # TODO: the history colletion should not really be history but rather status of each query. cache whether the query was too
    #       broad so the broad query can be done first the next time

    alphabet = list(string.ascii_lowercase)
    scraper = DCCourtsScraper()

    # allow restarting scraper from specific search query
    last_query = None
    search_queries = list(itertools.product(alphabet, repeat=3))
    last_index = search_queries.index(last_query) if last_query else 0

    for fname, lname1, lname2 in search_queries[last_query:]:

        search_query_str = str((fname, lname1, lname2))

        logging.info("Scraping %s" % search_query_str)

        # initialize search query
        try:
            scraper.start_search(fname, lname1+lname2)
        except ScraperException as e:
            logging.error(t.red("scraper encountered an error for query %s: %s" % (search_query_str, str(e))))
            db.history.insert({"_id": datetime.datetime.now(), "status": "error", "search_query": scraper.search_query, "error": str(e)})
            continue

        # perhaps just throw an error for this, catch it in the scraper and do a more refined query
        if scraper.query_too_broad:
            logging.warning(t.red("search query %s is too broad, limitted to %s search results" % (search_query_str, num_text)))

        # get expected number of results
        metadata = scraper.get_search_metadata()
        num_results = metadata['num_results']
        logging.info("Expecting %d results for query %s" % (num_results, search_query_str))

        try:
            # iterate through search result pages
            rows = []
            for i, row in enumerate(scraper.get_search_data()):
                row['_id'] = row.pop('case_number')
                try:
                    db.cases.insert(row)
                    logging.debug("inserted case: %s" % row['_id'])
                except pymongo.errors.DuplicateKeyError as e:
                    logging.debug("duplicate case: %s" % row['_id'])
                rows.append(row)
            logging.info(t.green("downloaded %d results for query %s" % (len(rows), search_query_str)))
            db.history.insert({"_id": datetime.datetime.now(), "status": "success", **metadata})
        except ScraperException as e:
            logging.error(t.red("scraper encountered an error for query %s: %s" % (search_query_str, str(e))))
            db.history.insert({"_id": datetime.datetime.now(), "status": "error", **metadata, "error": str(e)})
            continue

        # # initialize case details page
        # scraper.start_details()

        # # iterate through case details for given search query
        # for i, item in enumerate(scraper.get_detail_data()):
        #     print(i, item)

if __name__ == "__main__":
    main()
