from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests as rq
import datetime as dt

import argparse as ap
from xml.dom import minidom
from requests.models import HTTPError
# import logging


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/drive.file'
          ]


# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = ""
READ_RANGE_NAME = ""
WRITE_RANGE_NAME = ""


def call_request_github(url):
    return rq.get(url, auth=(username, token))


def isURLvalid(url):
    try:
        r = call_request_github(url)
        r.raise_for_status()
    except HTTPError:
        return False

    return True


def get_languages(url):
    r = call_request_github(url+'/languages')
    return ', '.join(list(r.json().keys())[:3])


def get_contributers_number(url):
    r = call_request_github(url + "/contributors")
    return len(r.json())


def get_last_pr_update(url):
    open_pr_date = None
    closed_pr_date = None

    try:
        r1 = call_request_github(url)
        r1.raise_for_status()
        r2 = call_request_github(url + "?per_page=1&state=close")
        r2.raise_for_status()

        try:
            # 'open' PR
            open_pr_date = dt.datetime.strptime(
                r1.json()[0]["created_at"], "%Y-%m-%dT%H:%M:%S%z").date()
        except IndexError:
            pass

        # 'closed' PR
        closed_pr_date = dt.datetime.strptime(
            r2.json()[0]['closed_at'], "%Y-%m-%dT%H:%M:%S%z").date()
    except IndexError:
        pass
    finally:
        return open_pr_date if \
            open_pr_date and \
            (not closed_pr_date or closed_pr_date < open_pr_date) \
            else closed_pr_date


def get_last_commit_date(url):
    r = call_request_github(url)
    try:
        r.raise_for_status()
        return dt.datetime.strptime(
            r.json()[0]['commit']['committer']['date'],
            "%Y-%m-%dT%H:%M:%S%z"
        ).date().isoformat()
    except HTTPError:
        return '-'


def get_ghaction_circle(url):
    actions = False
    circle = False
    travis = False
    r1 = call_request_github(url+"/actions/workflows")
    r1.raise_for_status()
    r2 = call_request_github(url+"/contents")
    r2.raise_for_status()
    # r3 = call_request_github(url+"/")
    ret_str = []
    try:
        actions = r1.json().get('total_count', 0) > 0
    except IndexError:
        pass

    if actions:
        ret_str.append('Actions')

    try:
        circle = any(item['name'] == '.circleci' for item in r2.json())
    except IndexError:
        pass

    if circle:
        ret_str.append('Circle')

    try:
        travis = any(item['name'] == '.travis.yml' for item in r2.json())
    except IndexError:
        pass

    if travis:
        ret_str.append('Travis')

    return '-'.join(ret_str) if ret_str else 'None'


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
    print('https://api.travis-ci.org/'+'/'.join(url.split('/')[3:6])+'/builds')

    try:
        r1.raise_for_status()
        r = r1
    except HTTPError:
        try:
            r2.raise_for_status()
            r = r2
        except HTTPError:
            return "NA"

    # print(r.text)
    # exit(1)
    # return "NA"
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
    url_blocks = url.split('.git')[0].rstrip('/$').split('#')[0].split("/")
    if len(url_blocks) < 5:
        return ['-', '-', '-', '-', '-']
    api_url = '/'.join(['https:/', 'api.github.com', 'repos', url_blocks[-2],
                        url_blocks[-1]])
    if not isURLvalid(api_url):
        return ['-', '-', '-', '-', '-']

    last_pr_date = get_last_pr_update(api_url + "/pulls")
    if isinstance(last_pr_date, dt.date):
        last_pr_date = last_pr_date.isoformat()
    else:
        last_pr_date = '-'

    return [
        get_languages(api_url),
        get_contributers_number(api_url),
        last_pr_date,
        get_last_commit_date(api_url + "/commits"),
        get_ghaction_circle(api_url),
        #    get_travis_build_failure_date(api_url)
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
    write_data = [[
        "Languages",
        "No of Contributers",
        "Last PR updated",
        "Last commit",
        "GH actions and/or Circle CI",
        #               "Last Travis build failed"
    ]]
    body = {
        "values": write_data
    }
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
                    write_data.append(['-', '-', '-', '-', '-'])
                    continue
                name = row[0]
                url = row[3]
                if url is not None and url.strip() != "":
                    print(i, name, url)
                    write_data.append(get_github_api_data(url))
            except IndexError:
                write_data.append(['-', '-', '-', '-', '-'])
                continue
            except HTTPError:
                print('***HTTP ERROR****')  # Logging
                write_data.append(['-', '-', '-', '-', '-'])
                continue

        response = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID, range=WRITE_RANGE_NAME,
            valueInputOption='RAW', insertDataOption='OVERWRITE',
            body=body
        ).execute()

        print(response['updates']['updatedRows'])


parser = ap.ArgumentParser('Get details of github projects\n')
parser.add_argument('--username', '-u', type=str, required=True,
                    help='Github username')
parser.add_argument('--token', '-t', type=str, required=True,
                    help='Github token for API (check github docs for API)')
parser.add_argument('--spreadsheet_id', '-sid', type=str, required=True,
                    help='Spreadsheet id from Google docs')
parser.add_argument('--read_sheet_name', '-rsheet', type=str, required=True,
                    help='Sheet name in Spreadsheet to read from')
parser.add_argument('--read_colrange', '-rrange', type=str, required=True,
                    help='Read column range in sheet')
parser.add_argument('--write_sheet_name', '-wsheet', type=str, required=False,
                    help='Sheet name in Spreadsheet to write, default --read_sheet_name')
parser.add_argument('--write_colrange', '-wrange', type=str, required=True,
                    help='Write column range in sheet')

username = parser.parse_args().username
token = parser.parse_args().token
sid = parser.parse_args().spreadsheet_id
rsheet = parser.parse_args().read_sheet_name
wsheet = parser.parse_args().write_sheet_name
rrange = parser.parse_args().read_colrange
wrange = parser.parse_args().write_colrange


SPREADSHEET_ID = sid
READ_RANGE_NAME = rsheet+'!'+rrange
WRITE_RANGE_NAME = wsheet+'!'+wrange if wsheet else rsheet+'!'+wrange
print()
if __name__ == "__main__":
    main()
