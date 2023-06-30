import requests
import re
import json
import csv
from datetime import date

def get_relchk(text):
    relchk = re.search('(?<=relchk=)[0-9]+', text).group(0)
    return relchk


def get_session_id(text):
    session_id = re.search('(?<=session=)[0-9]+', text).group(0)
    return session_id


def get_verification(text):
    verification_id = re.search('(?<=https://mvs.wiu.edu:3000/cics/webs/SCR414L\?)[a-z0-9]{8}', text).group(0)
    return verification_id


def get_dept_numbers():
    text = get_connection_page().text
    id_line = re.search(r'<select name=\"DEPT\" [-A-Za-z0-9\t .=\":<>&/]+', text)
    id_sections = re.findall('<option value=\"[0-9]+\" >', text)
    id_list = []
    for section in id_sections:
        raw_id = re.search('[0-9]+', section).group(0)
        if raw_id not in id_list:
            id_list.append(raw_id)
    return id_list


def get_connection_page():
    fetch_config = {"prog": "scr414l"}
    return requests.get('https://mvs.wiu.edu:3000/cics/webs/TCW880L', params=fetch_config)


def get_session():
    r = get_connection_page()
    relchk = get_relchk(r.text)
    session = get_session_id(r.text)
    raw_params = "?" + get_verification(r.text) + "&session=" + session + "&relchk=" + relchk
    return raw_params, session, relchk


def get_course_jsons(id_list):
    raw_page_returns = []
    failed_ids = []
    for dept_id in id_list:
        raw_params, session, relchk = get_session()

        request_payload["DEPT"] = dept_id
        request_payload["DFH_STATE_TOKEN"] = session
        request_payload["DFH_RELOAD_CHECK"] = relchk

        p = requests.request("POST", "https://mvs.wiu.edu:3000/cics/webs/SCR414L" + raw_params, data=request_payload)

        try:
            class_json = re.search(
                '(?<=<div id=\"JSONDATA\" class=\"noDisplay\">\r)(.)+(?=</div><!--Close JSONDATA Div-->)', p.text,
                re.DOTALL).group(0)
            raw_page_returns.append(class_json)
        except:
            failed_ids.append(dept_id)

    return raw_page_returns, failed_ids


# Pulled directly from browser tools
request_payload = {"DFH_STATE_TOKEN": "02396","DFH_RELOAD_CHECK":"05507280","DISPLAY_MENU":"","SCROLLPOS":"0","WINDOWWIDTH":"1920","WINDOWHEIGHT":"466","STARSFAQS":"","PLACEHOLDER":"","BUTTON_SEARCH":"Search","TERM":"202008 ","LOCATION":" ","DEPT":"+","COURSE":"","COURSE_LEVEL":"U","COURSE_CATEGORY":" ","BEG_HOUR":"06","BEG_MINUTE":"00","BEG_AM_PM":"A","END_HOUR":"11","END_MINUTE":"00","END_AM_PM":"P","ANY_DAY_CHECK":"X","INCLUDE_ARR_CHECK":"X","SORT_BY_IND":"D","CREDIT_HOURS":"  ","CLOSED_COURSES_IND":"Y","INSTRUCTOR":""}

classes, failed = get_course_jsons(get_dept_numbers())
recovered_classes, failed_again = get_course_jsons(failed)
final_recovery, ignore = get_course_jsons(failed_again)

classes.extend(recovered_classes)
classes.extend(final_recovery)

csv_prep = []
gathered = []
for json_return in classes:
    j = json.loads(json_return)

    for c in j["courses"]:
        print(c)
        course = {"Stars #": c["StarNumber"],
                  "Title": c["CourseInfo"]["Title"],
                  "Dept": c["CourseInfo"]["Abbr"],
                  "Number": c["CourseInfo"]["CourseNumber"],
                  "Professor": c["CourseInfo"]["Instr01"],
                  "Maximum": c["CourseInfo"]["MaxEnrollment"],
                  "Current": c["CourseInfo"]["CurEnrollment"],
                  "Location": c["CourseInfo"]["Location"],
                  "CreditHours": c["CourseInfo"]["CreditHours"]}
        if c["StarNumber"] not in gathered:
            csv_prep.append(course)
            gathered.append(c["StarNumber"])

with open(date.today().strftime("%Y-%m-%d Course Report") + '.csv', 'w', newline="") as csvfile:
    fieldnames = ["Stars #", "Title", "Dept", "Number", "Professor", "Maximum", "Current", "Location", "CreditHours"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for c in csv_prep:
        writer.writerow(c)
