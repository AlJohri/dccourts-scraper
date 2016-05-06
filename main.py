from __future__ import print_function
from __future__ import division

import string, itertools, logging
from dccourts_scraper import DCCourtsScraper, ScraperException

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler("scraper.log"),
                              logging.StreamHandler()])

logging.getLogger('requests').setLevel(logging.WARN)

from blessings import Terminal
t = Terminal()

alphabet = list(string.ascii_lowercase)
scraper = DCCourtsScraper()

# allow restarting scraper from specific search query
last_query = None
search_queries = list(itertools.product(alphabet, repeat=3))
last_index = search_queries.index(last_query) if last_query else 0

for fname, lname1, lname2 in search_queries[last_query:]:

    search_query = str((fname, lname1, lname2))

    logging.info("Scraping %s" % search_query)

    # initialize search query
    try:
        scraper.start_search(fname, lname1+lname2)
    except ScraperException as e:
        logging.exception("scraper encountered an error for query %s" % search_query)
        continue

    # get expected number of results
    metadata = scraper.get_search_metadata()
    num_results = metadata['num_results']
    logging.info("Expecting %d results for query %s" % (num_results, search_query))

    # iterate through search result pages
    rows = []
    for i, row in enumerate(scraper.get_search_data()):
        print(i, row)
        rows.append(row)

    try:
        assert(num_results == len(rows))
        logging.info("Downloaded %d results for query %s" % (len(rows), search_query))
    except AssertionError as e:
        logging.warn(t.red("for query %s number of expected results %d did not "
                           "match number of returned results %d" % (search_query, num_results, len(rows))))

    print('------------------------------')


    # # initialize case details page
    # scraper.start_details()

    # # iterate through case details for given search query
    # for i, item in enumerate(scraper.get_detail_data()):
    #     print(i, item)