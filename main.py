from __future__ import print_function
from __future__ import division

import string, itertools
from dccourts_scraper import DCCourtsScraper, ScraperException

alphabet = list(string.ascii_lowercase)
scraper = DCCourtsScraper()

# allow restarting scraper from specific permutation
last_permutation = None # ('a', 'g', 'u')
permutations = list(itertools.permutations(alphabet, 3))
last_index = permutations.index(last_permutation) if last_permutation else 0

for fname, lname1, lname2 in permutations[last_index:]:

    print("Scraping", fname, lname1, lname2)

    # initialize search query
    try:
        scraper.start_search(fname, lname1+lname2)
    except ScraperException as e:
        print(e)
        continue

    # iterate through search result pages
    metadata = scraper.get_search_metadata()
    num_results = metadata['num_results']
    print("Expecting %d results" % num_results)

    for i, row in enumerate(scraper.get_search_data()):
        print(i, row)

    print('------------------------------')

    # # initialize case details page
    # scraper.start_details()

    # # iterate through case details for given search query
    # for i, item in enumerate(scraper.get_detail_data()):
    #     print(i, item)