from contest_platform import ContestInfo, ContestPlatform
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List
import logging
import shelve
import sys

class ContestDatabase:
  @dataclass
  class Record:
    contest: ContestInfo
    notified_today: bool = False
    notified_1hr: bool = False
    notified_15min: bool = False

  def __init__(self, filename: str, platforms: List[ContestPlatform]):
    self.filename = filename
    self.platforms = platforms

  def update(self) -> None:
    with shelve.open(self.filename, writeback=True) as db:
      self.__update(db)
      self.__cleanup(db)

  def notifications(self) -> List[ContestInfo]:
    notifications = []
    with shelve.open(self.filename, writeback=True) as db:
      for uid in db.keys():
        contest = db[uid].contest
        if contest.start_time - datetime.now() <= timedelta(minutes=15):
          if db[uid].notified_15min:
            continue

          db[uid].notified_15min = True
          db[uid].notified_1hr = True
          db[uid].notified_today = True
          notification = f'{contest.fullname} starting in 15 minutes!\n'
          notification += f'Link: {contest.link}'
          logging.info(f'Notifying (15 mins): {uid}')
          notifications.append(notification)
        
        elif contest.start_time - datetime.now() <= timedelta(hours=1):
          if db[uid].notified_1hr:
            continue

          db[uid].notified_1hr = True
          db[uid].notified_today = True
          notification = f'{contest.fullname} starting in an hour!\n'
          notification += f'Link: {contest.link}'
          logging.info(f'Notifying (1 hr): {uid}')
          notifications.append(notification)

        elif contest.start_time.date() == datetime.today().date():
          if db[uid].notified_today:
            continue

          db[uid].notified_today = True
          logging.info(f'Notifying (today): {uid}')
          notifications.append(contest)

    return notifications

  def __update(self, db):
    for platform in self.platforms:
      try:
        for contest in platform.upcoming_contests():
          if contest.uid in db:
            logging.info(f'Updating {contest.uid}')
            db[contest.uid].contest = contest
          else:
            logging.info(f'Inserting {contest.uid}')
            db[contest.uid] = ContestDatabase.Record(contest)
      except Exception as e:
        logging.error(e)

  def __cleanup(self, db):
    for uid in list(db.keys()):
      if db[uid].contest.start_time <= datetime.now():
        logging.info(f'Removing {uid}')
        del db[uid]

if __name__ == '__main__':
  assert(len(sys.argv) == 2)
  with shelve.open(sys.argv[1]) as db:
    for record in db.values():
      contest = record.contest
      print('uid:', contest.uid)
      print(contest)
      print(f'notified_today: {record.notified_today}')
      print(f'notified_1hr: {record.notified_1hr}')
      print(f'notified_15min: {record.notified_15min}')
      print()