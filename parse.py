# COPYRIGHT AYDAR N. (me@aydar.media)
#
# 2022 - 2023
#

import requests
from bs4 import BeautifulSoup
import bs4
from ics import Calendar, Event, DisplayAlarm
import ics
from transliterate import translit
from datetime import datetime, timedelta
import sys

EMAIL = "aetimofeev@edu.hse.ru"
PWD = "2022"
GLOBAL_CALENDARS_PATH = "/var/www/html/mutt/"
VERSION = "0.3.3"
FINAL_WORD = "❇️ aydar.media"
REPO_URL = "https://timetracker.hse.ru"
FINAL_URL = "https://timetracker.hse.ru/schedule.aspx?organizationId=1&facultyids=1&course="
BASE_DAY = 4
COURSES = [1, 2, 3]
BANLIST = [
	"История и теория",
	"Английский язык",
	"Военная подготовка",
	"Майнор",
	"3D-печать",
	"Ювелирный дизайн",
	"Светодизайн",
	"вариативных",
	
]

VERBOSE = "--verbose" in sys.argv

def log(message):
	if VERBOSE:
		print(message)
def die(message):
	print(f'FATAL: {message}')
	exit(1)
def get_date(dow):
	days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
	day = str(BASE_DAY + days.index(dow))
	if len(day) == 1:
		return f"0{day}"
	else:
		return day

class Group:
	def __init__(self, title):
		self.title = title
		self.lectures = []
class Lecture:
	def __init__(self, title, dow, start_time, end_time, location, lector, desc):
		self.title = title
		self.dow = dow
		self.start_time = start_time
		self.end_time = end_time
		self.location = location
		if lector is None:
			self.lector = "Нет информации о преподавателе"
		else:
			self.lector = "Ведет " + lector
		if desc is None:
			self.desc = "Нет доп. информации"
		else:
			self.desc = desc

if "-v" in sys.argv or "--version" in sys.argv:
	print(f"Mutt v{VERSION}")
	exit(0)
if "--clear-output" in sys.argv:
	import glob
	import os
	out = glob.glob(os.path.join(GLOBAL_CALENDARS_PATH, '*.ics'))
	for file in out:
		os.remove(file)
		log(f'Removed {file}')
	exit(0)

log('Fetching login form...')
response = requests.get("https://timetracker.hse.ru/login.aspx")
if response.status_code != 200:
	die(f"Round 1: Got {response.status_code} code (expected 200), dying...")
response = BeautifulSoup(response.text, features="lxml")
vs = response.find("input", attrs={"id":"__VIEWSTATE"})["value"]
vsg = response.find("input", attrs={"id":"__VIEWSTATEGENERATOR"})["value"]
ev = response.find("input", attrs={"id":"__EVENTVALIDATION"})["value"]

headers = {
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	"Origin": "https://timetracker.hse.ru",
	"Content-Type": "application/x-www-form-urlencoded",
	"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
	"Referer": "https://timetracker.hse.ru/login.aspx",
}

data = {
	"__EVENTTARGET": "ctl00$cplhMainContent$lbLogin",
	"__EVENTARGUMENT": "",
	"__VIEWSTATE": vs,
	"__VIEWSTATEGENERATOR": vsg,
	"__EVENTVALIDATION": ev,
	"ctl00$cplhMainContent$txtEmail": EMAIL,
	"ctl00$cplhMainContent$txtPassword": PWD,
	"ctl00$cplhMainContent$ddlOrganizations": "1",
}

log('Attempting login...')
response = requests.post("https://timetracker.hse.ru/login.aspx", headers=headers, data=data, allow_redirects=False)
if response.status_code != 302:
	# with open("./txt.html", "w") as file:
	# 	file.write(response.text)
	die(f"Round 2: Got {response.status_code} code (expected 302), dying...")
jar = response.cookies

groups = {}

for course in COURSES:
	log(f'\nParsing course {course}...')
	course_url = FINAL_URL + str(course)

	response = requests.get(course_url, cookies=jar)
	if response.status_code != 200:
		die(f"Round 3: Got {response.status_code} code (expected 200), dying...")

	response = BeautifulSoup(response.text, features="lxml")

	log(f'  Parsing groups...')
	groups[course] = []
	for i in response.find("table", attrs={"class":"schedule-table"}).thead.tr:
		if i.string is not None:
			continue
		group_name = translit(i.b.string.split(" ")[0], "ru", reversed=True)
		log(f'    Found group {group_name}')
		groups[course].append(Group(group_name))

	log(f'  Parsing timetable...')
	for row in response.find("table", attrs={"class":"schedule-table"}).tbody:
		index = 0
		for cell in row:
			if type(cell) is not str and cell.string is not None and cell.string != "\n":
				txt = cell.string.strip().replace('\n', '')
				if len(txt) == 13:
					time = txt.split("-")
				elif len(txt) == 2:
					dow = txt
				else:
					die(f"Could not parse text instance '{txt}'")
			elif type(cell) is not bs4.element.NavigableString:
				nc = BeautifulSoup(str(cell), features="lxml")
				a = nc.find_all("div")
				sp = nc.find_all("span")
				desc = None
				for k in sp:
					desc = k.get_text().replace("\n", "").strip()
					k.replaceWith("")
				need_append = False
				for k in a:
					if k.get("class") == ["discipline"]:
						discipline = k.get_text().strip()
						need_append = True
						aud = None
						lec = None
					elif k.get("class") == ["auditory"]:
						aud = k.get_text()
					elif k.get("class") == ["user"]:
						lec = k.get_text()
					elif k.get("class") == ["comment"]:
						if desc is None:
							desc = k.get_text()
						else:
							desc += ("\n" + k.get_text())
				if need_append:
					if not any(banned in discipline for banned in BANLIST):
						lecture = Lecture(discipline, dow, time[0].strip(), time[1].strip(), aud, lec, desc)
						groups[course][index - 1].lectures.append(lecture)
						log(f'      Appended "{discipline} to group {groups[course][index - 1].title}"')
					else:
						log(f'      Skipped "{discipline}"')
				index += 1

for i in [item for sublist in groups.values() for item in sublist]:
	log(f'\nCreating events for group "{i.title}"...')
	c = Calendar()
	for j in i.lectures:
		log(f'  Creating lecture "{j.title}"...')
		e = Event()
		e.name = j.title
		e.begin = f"2023-09-{get_date(j.dow)}T{j.start_time}:00.000000+03:00"
		e.end = f"2023-09-{get_date(j.dow)}T{j.end_time}:00.000000+03:00"
		e.location = j.location
		e.description = f"{j.lector}\n{j.desc}\n\n{FINAL_WORD}"
		e.url = REPO_URL
		e.extra.append(ics.grammar.parse.ContentLine(name="RRULE", value="FREQ=WEEKLY;INTERVAL=1"))
		alarm = DisplayAlarm(trigger=timedelta(minutes=-5), display_text="Бегом учиться!!!")
		e.alarms.append(alarm)
		c.events.add(e)
	trans = translit(i.title.split(" ")[0], "ru", reversed=True)
	with open(f"{GLOBAL_CALENDARS_PATH}{i.title}.ics", "w") as file:
		file.writelines(c.serialize_iter())
	log(f'Wrote group "{i.title}"')
