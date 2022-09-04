import requests
from bs4 import BeautifulSoup
import bs4
from ics import Calendar, Event
import ics

EMAIL = "aanasibullin@edu.hse.ru"
PWD = "2022"

headers = {
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	"Origin": "https://timetracker.hse.ru",
	"Content-Type": "application/x-www-form-urlencoded",
	"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
	"Referer": "https://timetracker.hse.ru/Login.aspx?ReturnUrl=%2f",
}

data = {
	"__EVENTTARGET": "ctl00$cplhMainContent$lbLogin",
	"__EVENTARGUMENT": "",
	"__VIEWSTATE": "UJckLVRoGXv3oSPq4frGUwpzTOlFubZYHUP2fTztwhO2uDASb13yKrAN/XdTANRC5/AYAA2HRGCE/qOn4HmhZq25/LdkwbpMkl5Zg1fi52ff+m+A",
	"__VIEWSTATEGENERATOR": "C2EE9ABB",
	"__EVENTVALIDATION": "91OKamAqj3Jx6vNh3Uxmw2EUS3BPKfjCddehBND3nQNwznkMAIfwqpRXc7A4LvqAbtKU+xRgMNxN4HVI9NxkbpGAQtKJESUtQUSoWdobQ7S568YNcMk0Wazp2eycTGAob128x3ggzEVUwRJIPjl0HCtR1GOFFFRTsJRNcjZ2o5mj7304J7DPQH+MO3et0FXh5zLyO9R5k62Nr25tKfk4YezFmqg=",
	"ctl00$cplhMainContent$txtEmail": EMAIL,
	"ctl00$cplhMainContent$txtPassword": PWD,
	"ctl00$cplhMainContent$ddlOrganizations": "1",
}

class Group:
	def __init__(self, title):
		self.title = title
		self.lectures = []
class Lecture:
	def __init__(self, title, dow, start_time, end_time):
		self.title = title
		self.dow = dow
		self.start_time = start_time
		self.end_time = end_time

def die(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
	exit(1)
def get_date(dow):
	match dow:
		case "ПН":
			return "05"
		case "ВТ":
			return "06"
		case "СР":
			return "07"
		case "ЧТ":
			return "08"
		case "ПТ":
			return "09"
		case "СБ":
			return "10"
		case "ВС":
			return "11"

response = requests.post("https://timetracker.hse.ru/login.aspx", headers=headers, data=data, allow_redirects=False)
if response.status_code != 302:
	die(f"Got {response.status_code} code (expected 302), dying...")
jar = response.cookies
redirect = response.headers["Location"]
response = requests.get(redirect, cookies=jar)
if response.status_code != 200:
	die(f"Got {response.status_code} code (expected 200), dying...")

# with open("/Users/lesterrry/Кэш/txt.html", "r") as file:
# 	response = file.read()

response = BeautifulSoup(response.text, features="lxml")

groups = []

for i in response.find("table", attrs={"class":"schedule-table"}).thead.tr:
	if i.string is not None:
		continue
	groups.append(Group(i.b.string))

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
			for k in sp:
				k.replaceWith("")
			for k in a:
				if k.get("class") == ["discipline"]:
					txt = k.get_text().strip()
					groups[index - 1].lectures.append(Lecture(txt, dow, time[0].strip(), time[1].strip()))
					break
			index += 1

for i in groups:
	c = Calendar()
	for j in i.lectures:
		e = Event()
		e.name = j.title
		e.begin = f"2022-09-{get_date(j.dow)}T{j.start_time}:00.000000+03:00"
		e.end = f"2022-09-{get_date(j.dow)}T{j.end_time}:00.000000+03:00"
		e.extra.append(ics.grammar.parse.ContentLine(name="RRULE", value="FREQ=WEEKLY;INTERVAL=1"))
		c.events.add(e)
	with open(f"{i.title.split(' ')[0]}.ics", "w") as file:
		file.writelines(c.serialize_iter())