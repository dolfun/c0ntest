from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
import re

from bs4 import BeautifulSoup
import requests

@dataclass
class ContestInfo:
  uid: str
  platform: str
  name: str
  link: str
  start_time: datetime
  duration_in_mins: int
  remark: str = ''

  @property
  def fullname(self) -> str:
    if self.platform in self.name:
      return self.name
    else:
      return f'{self.platform} {self.name}'

  @property
  def start_time_str(self) -> str:
    days, hours = divmod(self.duration_in_mins, 24 * 60)
    hours, minutes = divmod(hours, 60)

    text = ''
    if days > 0: text += f'{days} day'
    if days > 1: text += 's'
    text += ' '

    if hours > 0: text += f'{hours} hour'
    if hours > 1: text += 's'
    text += ' '

    if minutes > 0: text += f'{minutes} minute'
    if minutes > 1: text += 's'

    return text.lstrip().rstrip()

  def __str__(self):
    text = ''
    text += self.fullname + '\n'
    text += self.start_time.strftime('%d %b %Y, %I:%M %p\n')
    text += f'Duration: {self.start_time_str}\n'
    text += f'Link: {self.link}'
    if len(self.remark) > 0: text += f'\n**{self.remark}**'
    return text

class ContestPlatform(ABC):
  @abstractmethod
  def upcoming_contests(self) -> List[ContestInfo]:
    pass

class Codeforces(ContestPlatform):
  def upcoming_contests(self) -> List[ContestInfo]:
    upcoming_contests = []

    response = requests.get('https://codeforces.com/api/contest.list')
    if response.status_code != 200:
      return upcoming_contests

    response = response.json()
    for contest in response['result']:
      if contest['phase'] != 'BEFORE':
        continue

      contest_id = contest['id']
      contest_info = ContestInfo(
        uid=f'codeforces-{contest_id}',
        platform='Codeforces',
        name = contest['name'],
        link = f'https://codeforces.com/contest/{contest_id}',
        start_time = datetime.fromtimestamp(contest['startTimeSeconds']),
        duration_in_mins=int(contest['durationSeconds'])//60
      )

      if contest_info.start_time.hour != 20:
        contest_info.remark = 'Notice the unusual time!'

      upcoming_contests.append(contest_info)

    return upcoming_contests
  
class Codechef(ContestPlatform):
  def upcoming_contests(self) -> List[ContestInfo]:
    upcoming_contests = []

    response = requests.get('https://www.codechef.com/api/list/contests/all?sort_by=START&sorting_order=asc&offset=0&mode=all')
    if response.status_code != 200:
      return upcoming_contests

    response = response.json()
    for contest in response['future_contests']:
      contest_id = contest['contest_code']
      contest_info = ContestInfo(
        uid=f'codechef-{contest_id}',
        platform='Codechef',
        name=contest['contest_name'],
        link=f'https://www.codechef.com/{contest_id}',
        start_time=datetime.fromisoformat(contest['contest_start_date_iso']).replace(tzinfo=None),
        duration_in_mins=int(contest['contest_duration'])
      )

      upcoming_contests.append(contest_info)

    return upcoming_contests
  
class AtCoder(ContestPlatform):
  def upcoming_contests(self) -> List[ContestInfo]:
    upcoming_contests = []
    response = requests.get('https://atcoder.jp/contests')
    if response.status_code != 200:
      return upcoming_contests
    
    soup = BeautifulSoup(response.text, 'html.parser')
    info = soup.find('div', id='contest-table-upcoming').table.tbody
    for row in info.find_all('tr'):
      entries = row.find_all('td')
      if len(entries) != 4:
        continue

      contest_name = entries[1].find('a').text.replace('  ', ' ')
      contest_name = re.sub(r'\s+', ' ', contest_name)
      pattern = r'AtCoder (Beginner|Regular|Heuristic) Contest (\d+)'
      matches = re.findall(pattern, contest_name)
      if len(matches) == 0:
        continue

      contest_type, contest_nr = matches[0]
      contest_id = entries[1].find('a')['href'].split('/contests/')[-1]
      hours, minutes = entries[2].text.split(':')
      contest_info = ContestInfo(
        uid=f'atcoder-{contest_id}',
        platform='AtCoder',
        name=f'AtCoder {contest_type} Contest {contest_nr}',
        link=f'https://atcoder.jp/contests/{contest_id}',
        start_time=self.__parse_timeanddate_url(entries[0].find('a')['href']),
        duration_in_mins=60*int(hours)+int(minutes)
      )

      if contest_type == 'Heuristic':
        contest_info.remark = 'This is a Heuristic contest!'

      upcoming_contests.append(contest_info)

    return upcoming_contests
  
  def __parse_timeanddate_url(self, url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    iso_value = query_params.get('iso', [None])[0]
    datetime_obj = datetime.fromisoformat(iso_value).replace(tzinfo=None)
    return datetime_obj - timedelta(hours=3.5)
  
class LeetCode(ContestPlatform):
  def upcoming_contests(self) -> List[ContestInfo]:
    upcoming_contests = []

    headers = { 'Content-Type': 'application/json' }
    json = { 'query': 'query topTwoContests { topTwoContests { title titleSlug startTime duration } }' }
    response = requests.post('https://leetcode.com/graphql/', headers=headers, json=json)
    for contest in response.json()['data']['topTwoContests']:
      contest_info = ContestInfo(
        uid=f'leetcode-{contest['titleSlug']}',
        platform='LeetCode',
        name=contest['title'],
        link=f'https://leetcode.com/contest/{contest['titleSlug']}',
        start_time = datetime.fromtimestamp(contest['startTime']),
        duration_in_mins=int(contest['duration'])//60
      )

      if 'Weekly' in contest_info.name:
        contest_info.remark = 'Contest is in morning!'

      upcoming_contests.append(contest_info)

    return upcoming_contests

def get_platforms():
  return [Codeforces(), Codechef(), AtCoder(), LeetCode()]

if __name__ == '__main__':
  platforms = get_platforms()
  for platform in platforms:
    for contest in sorted(platform.upcoming_contests(), key=lambda contest: contest.start_time):
      print(contest)
      print()