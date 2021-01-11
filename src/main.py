from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests as rq
from datetime import date, datetime as dt
import argparse as ap
from xml.dom import minidom
from requests.api import request
from requests.models import HTTPError
import pprint


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/drive.file'
          ]


# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = "1ND3SnMHpbFYeNjvU9gDNIuCP3a2-Q_xzxbtyl18V_8s"
READ_RANGE_NAME = "ubuntu2004!A2:P"
WRITE_RANGE_NAME = "ubuntu2004!Q1:U"


def call_request_github(url):
    return rq.get(url, auth=(username, token))


def get_api_url(url):
    url_parts = url.split("/")
    return "https://api.github.com/repos/" + url_parts[-2] + "/" \
                                           + url_parts[-1]


def get_contributers_number(url):
    r = call_request_github(url + "/contributors")
    return len(r.json())


def get_last_pr_update(url):
    open_pr_date = date(1900, 1, 1)
    closed_pr_date = date(1900, 1, 1)

    r1 = call_request_github(url)
    r1.raise_for_status()
    r2 = call_request_github(url + "?per_page=1&state=close")
    r2.raise_for_status()

    try:
        # 'open' PR
        open_pr_date = dt.strptime(
            r1.json()[0]["created_at"], "%Y-%m-%dT%H:%M:%S%z").date()
    except IndexError:
        pass

    try:
        # 'closed' PR
        closed_pr_date = dt.strptime(
            r2.json()[0]['closed_at'], "%Y-%m-%dT%H:%M:%S%z").date()
    except IndexError:
        return open_pr_date if closed_pr_date == "" else closed_pr_date
    finally:
        return open_pr_date if closed_pr_date < open_pr_date\
            else closed_pr_date


def get_last_commit_date(url):
    r = call_request_github(url)
    return dt.strptime(r.json()[0]['commit']['committer']['date'],
                       "%Y-%m-%dT%H:%M:%S%z").date().isoformat()


def get_ghaction_circle(url):
    actions = False
    circle = False
    r1 = call_request_github(url+"/actions/workflows")
    r1.raise_for_status()
    r2 = call_request_github(url+"/contents")
    r2.raise_for_status()

    try:
        actions = r1.json().get('total_count', 0) > 0
    except IndexError:
        pass

    try:
        circle = any(item['name'] == '.circleci' for item in r2.json())
    except IndexError:
        pass

    if actions and circle:
        return 'Actions | Circle'

    if actions:
        return 'Actions'

    if circle:
        return 'Circle'

    return 'None'


def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


def is_travis_enabled(url):
    travis = False
    r = call_request_github(url)
    try:
        travis = any(item['name'] == '.travis.yml' for item in r.json())
    except IndexError:
        pass
    return travis


def get_travis_build_failure_date(url):
    if not is_travis_enabled(url+'/contents'):
        return "NA"

    r1 = rq.get(
        'https://api.travis-ci.com/'+'/'.join(url.split('/')[3:6])+'/builds',
        headers={"Accept": "application/atom+xml"}
    )
    r2 = rq.get(
        'https://api.travis-ci.org/'+'/'.join(url.split('/')[3:6])+'/builds',
        headers={"Accept": "application/atom+xml"}
    )

    try:
        r1.raise_for_status()
        r = r1
    except HTTPError:
        try:
            r2.raise_for_status()
            r = r2
        except HTTPError:
            return "NA"

    feed = minidom.parseString(r.text)
    entries = feed.getElementsByTagName("entry")
    for entry in entries:
        for summary in entry.getElementsByTagName('summary'):
            summary_string = "%s" % getText(summary.childNodes)
            if 'State: failed' in summary_string:
                linebyline = [i.strip().strip('</p>')
                              for i in summary_string.strip().split('\n')]
                return linebyline[-2].lstrip('Finished at: ')
    return "NA"


def get_github_api_data(url):
    api_url = get_api_url(url)
    no_of_contributors = get_contributers_number(api_url)
    last_pr_date = get_last_pr_update(api_url + "/pulls").isoformat()
    last_commit_on = get_last_commit_date(api_url + "/commits")
    ghaction_circle = get_ghaction_circle(api_url)
    last_failed_travis_build = get_travis_build_failure_date(api_url)
    return [
        no_of_contributors, last_pr_date, last_commit_on,
        ghaction_circle, last_failed_travis_build
    ]


def main():

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
            flow = InstalledAppFlow.from_client_secrets_file(
                "./credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("../token.pickle", "wb") as token:
            pickle.dump(creds, token)

    service = build("sheets", "v4", credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SPREADSHEET_ID, range=READ_RANGE_NAME)
        .execute()
    )
    values = result.get("values", [])

    # write_data = []
    write_data = [["No of Contributers", "Last PR updated", "Last commit",
                   "GH actions and/or Circle CI", "Last Travis build failed"]]
    if not values:
        print("No data found.")
    else:
        print("Index, Package, URL")
        for i, row in enumerate(values, 2):
            # Print columns A and E, which correspond to indices 0 and 3.
            # print("%s, %s" % (row[0], row[3]))
            try:
                if not row:
                    # raise IndexError
                    write_data.append(["", "", "", "", ""])
                    continue
                name = row[0]
                url = row[3]
                if url is not None and url.strip() != "":
                    print(i, name, url)
                    write_data.append(get_github_api_data(url))
            except IndexError:
                write_data.append(["", "", "", "", ""])
                continue

        body = {
            "values": write_data
        }

        response = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID, range=WRITE_RANGE_NAME,
            valueInputOption='RAW', insertDataOption='OVERWRITE',
            body=body
        ).execute()

        print(response['updates']['updatedRows'])


parser = ap.ArgumentParser('Get details of github projects\n')
parser.add_argument('--username', '-u', type=str,
                    required=True, help='Github username')
parser.add_argument('--token', '-t', type=str, required=True,
                    help='Github token for API (check github docs for API)'
                    )
username = parser.parse_args().username
token = parser.parse_args().token
if __name__ == "__main__":
    main()
