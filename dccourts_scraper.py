from __future__ import print_function
from __future__ import division

import requests, lxml.html, re, math, logging

from data import case_codes, party_codes, status_codes

from blessings import Terminal
t = Terminal()

valid_case_codes = list(case_codes.keys())
valid_party_codes = list(party_codes.keys())
valid_status_codes = list(status_codes.keys())

class DCCourtsScraper(object):
    """
    State based singleton scraper class. Makes new requests based off of previous request.
    If you make queries out of order, nothing will work.
    """

    url = "https://www.dccourts.gov/cco/maincase.jsf"
    num_per_page = 12

    # Generic
    # --------------------------------------------------------------------------------------- ##

    def __init__(self):
        self.reset()

    def reset(self):
        """
        Reset scraper by creating a new requests.Session and making an initial
        GET request to the DC Courts page to create a new JESSIONID cookie and
        allow us to grab the current JSF ViewState.
        """
        self.session = requests.Session()
        self.response = self.session.get(self.url) # initialize cookies
        self.doc = self._make_doc(self.response)
        self.viewstate = self._get_viewstate()

    def post(self, payload):
        payload.update({"javax.faces.ViewState": self.viewstate})
        self.response = self.session.post(self.url, data=payload)
        self.doc = self._make_doc(self.response)
        self.viewstate = self._get_viewstate()
        self._check_errors()
        return self.doc

    # Generic Helpers
    # --------------------------------------------------------------------------------------- ##

    def _make_doc(self, response):
        return lxml.html.fromstring(response.content)

    def _get_viewstate(self):
        return self.doc.cssselect("#javax\.faces\.ViewState")[0].get('value')

    def _check_errors(self):
        errors = self.doc.cssselect("li.errormessages")
        if len(errors) > 0:
            raise ScraperException("\n".join([error.text_content() for error in errors]))

    # Search
    # --------------------------------------------------------------------------------------- #

    def start_search(self, first_name, last_name, company_name="", case_code="", party_code="", status_code="", from_date="", to_date=""):
        if len(first_name) < 1: raise Exception()
        if len(last_name) < 2: raise Exception()

        if case_code and case_code not in valid_case_codes: raise ValueError("case code %s invalid" % case_code)
        if party_code and party_code not in valid_party_codes: raise ValueError("party code %s invalid" % party_code)
        if status_code and status_code not in valid_status_codes: raise ValueError("status code %s invalid" % status_code)

        self.search_query = {
            "first_name": first_name,
            "last_name": last_name,
            "company_name": company_name,
            "case_code": case_code,
            "party_code": party_code,
            "status_code": status_code,
            "from_date": from_date,
            "to_date": to_date,
        }

        payload = self._get_search_payload()

        self.current_page_number = 1
        self._process_search(payload)

    def get_search_metadata(self):
        return {
            "num_results": self.num_results
        }

    def get_search_data(self):
        for i, row in enumerate(self.data):
            row.append(self.current_page_number)
            yield row

        estimated_num_pages = int(math.ceil(self.num_results / self.num_per_page))

        for page_number in range(2, estimated_num_pages+1):
            self.current_page_number = page_number
            payload = self._get_next_search_page_payload()
            self._process_search(payload)

            for i, row in enumerate(self.data):
                row.append(self.current_page_number)
                yield row

    def _process_search(self, payload):
        self.post(payload)
        try:
            self.num_results = self._get_num_results()
            self.data = self._get_rows()
        except Exception as e:
            import pdb; pdb.set_trace()

    def _get_search_payload(self):
        return {
            "appData:searchform": "appData:searchform",
            "appData:searchform:searchPanelCollapsedState": "false",
            "appData:searchform:jspsearchpage:firstName": self.search_query['first_name'],
            "appData:searchform:jspsearchpage:lastName": self.search_query['last_name'],
            "appData:searchform:jspsearchpage:companyName": self.search_query['company_name'],
            "appData:searchform:jspsearchpage:jspattributespage:selectCaseCode": self.search_query['case_code'],
            "appData:searchform:jspsearchpage:jspattributespage:selectPartyCode": self.search_query['party_code'],
            "appData:searchform:jspsearchpage:jspattributespage:selectStatusCode": self.search_query['status_code'],
            "appData:searchform:jspsearchpage:jspattributespage:filedFromDate:j_id_id16pc4": self.search_query['from_date'],
            "appData:searchform:jspsearchpage:jspattributespage:filedToDate:j_id_id19pc4": self.search_query['to_date'],
            "appData:searchform:jspsearchpage:submitSearch": ""
        }

    def _get_next_search_page_payload(self):
        return {
            "appData:resultsform": "appData:resultsform",
            "appData:resultsform:resultsPanelCollapsedState": "false",
            "appData:resultsform:jspresultspage:bottomScroller": "next",
            "appData:resultsform:_idcl": "appData:resultsform:jspresultspage:bottomScrollernext"
        }

    def _get_num_results(self):
        text2parse = self.doc.cssselect("input[name=appData\:resultsform\:resultsPanelCollapsedState]")[0].getnext().text

        match1 = re.search(r"Search retrieved (\d+)", text2parse)
        if match1:
            num_text = match1.groups()[0]
        else:
            match2 = re.search(r"Search limited to (\d+)", text2parse)
            if match2:
                num_text = match2.groups()[0]
                logging.warning(t.red("search query %s is too broad, limitted to %s search results" % (str(self.search_query), num_text)))
            else:
                raise ScraperException("cannot find number of results for query %s" % (str(self.search_query)))
        return int(num_text)

    def _get_rows(self):
        table_rows = self.doc.cssselect("#appData\:resultsform\:jspresultspage\:dt1\:tbody_element > tr")
        rows = []
        for table_row in table_rows:
            rows.append([x.text_content() for x in table_row.cssselect("td:not(:first-child)")])
        return rows

    # Details
    # --------------------------------------------------------------------------------------- #

    def start_details(self):
        payload = {
            "appData:resultsform": "appData:resultsform",
            "appData:resultsform:resultsPanelCollapsedState": "false",
            "appData:resultsform:jspresultspage:dt1:j_id_id41pc5": ""
        }
        self._process_detail(payload)

    def _process_detail(self, payload):
        self.post(payload)

        docket_table = self.doc.cssselect("#appData\:detailsform\:jspdetailspage\:docketInfo\:DocketsInfo")[0]
        docket_tbody = self.doc.cssselect("#appData\:detailsform\:jspdetailspage\:docketInfo\:DocketsInfo\:tbody_element")[0]

        rows = []
        table_rows = docket_tbody.cssselect("* > tr")
        for table_row in table_rows:
            rows.append([x.text_content() for x in table_row.cssselect("td")])

        # doc.cssselect("div.detaildataformat")[0].text_content()
        self.detail_data = {
            "summary": self.doc.cssselect("div.casesummaryheader")[0].text_content().strip(),
            "dockets": rows
        }

    def get_detail_data(self):

        yield self.detail_data

        for i in range(self.num_results):
            payload = self._get_next_detail_item_payload()
            self._process_detail(payload)
            yield self.detail_data

    def _get_next_detail_item_payload(self):
        return {
            "appData:detailsform": "appData:detailsform",
            "appData:detailsform:detailsPanelCollapsedState": "false",
            "appData:detailsform:summaryCaseDetails:bottomNext": ""
        }

    # --------------------------------------------------------------------------------------- #

class ScraperException(Exception):
    pass
