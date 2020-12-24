from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests as rq
from datetime import date, datetime as dt
from json import decoder
import argparse as ap
# TODO : github api authentication for using github REST services.

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1ND3SnMHpbFYeNjvU9gDNIuCP3a2-Q_xzxbtyl18V_8s"
SAMPLE_RANGE_NAME = "ubuntu2004!A2:P"


def get_api_url(url):
    url_parts = url.split("/")
    return "https://api.github.com/repos/" + url_parts[-2] + "/" + url_parts[-1]


def get_contributers_number(url):
    r = rq.get(url + "/contributors")
    return len(r.json())


def get_last_pr_update(url):
    open_pr_date = date(1900, 1, 1)
    closed_pr_date = date(1900, 1, 1)

    r1 = rq.get(url)
    r2 = rq.get(url + "?per_page=1&state=closed")
    print(url + "?per_page=1&state=closed")

    try:
        # 'open' PR
        open_pr_date = dt.strptime(r1.json()[0]["created_at"], "%Y-%m-%dT%H:%M:%S%z").date()
    except IndexError:
        pass

    try:
        # 'closed' PR
        closed_pr_date = dt.strptime(r2.json()[0]["closed_at"], "%Y-%m-%dT%H:%M:%S%z").date()
    except IndexError:
        # print(open_pr_date, closed_pr_date)
        return open_pr_date if closed_pr_date == "" else closed_pr_date
    finally:
        return open_pr_date if closed_pr_date < open_pr_date else closed_pr_date


def get_last_commit_date(url):
    pass


def get_ghaction_circle(url):
    pass


def get_travis_build_failure_date(url):
    pass


def get_github_api_data(url):
    api_url = get_api_url(url)
    # No. of contributors:
    no_of_contributors = get_contributers_number(api_url)
    print(no_of_contributors)
    # Last PR filed on
    last_pr_date = get_last_pr_update(api_url + "/pulls")
    print(last_pr_date)
    # last change applied  =>  ,
    last_commit_on = get_last_commit_date(url)
    # any sign of a Circle CI or GitHub Actions config file,
    ghaction_circle = get_ghaction_circle(url)
    # Last time successful Travis build failed...
    last_failed_travis_build = get_travis_build_failure_date(url)
    # write_row(no_of_contributors, last_pr_date, last_commit_on, ghaction_circle, last_failed_travis_build)


def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("../token.pickle"):
        with open("../token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("../credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("../token.pickle", "wb") as token:
            pickle.dump(creds, token)

    service = build("sheets", "v4", credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
        .execute()
    )
    values = result.get("values", [])

    if not values:
        print("No data found.")
    else:
        print("Package, URL")
        for row in values:
            # Print columns A and E, which correspond to indices 0 and 3.
            # print("%s, %s" % (row[0], row[3]))
            if row[3] != "NA":
                get_github_api_data(row[3])


if __name__ == "__main__":
    arg_parser = ap.ArgumentParser()
    token = arg_parser.add_argument
    main()
