import parsec as p
import re
from src.util import padDigit 

def expandYear(x:str)->str:
  """Expand years: [1-9]X -> 19XX and 0X -> 200X"""
  if(len(x) == 2):
    if(x[0] == "0"):
      x =  "20" + x
    else:
      x = "19" + x
  return(x)


class Date:
  def __init__(self, year:str, month:str=None, day:str=None):
    self.year = year
    self.month = month
    self.day = day

  def __str__(self):
    return("-".join([self.month, self.day, self.year]))

# parse date
p_year = p.regex('20\d\d') ^ p.regex('19\d\d') ^ p.regex('\d\d').parsecmap(expandYear)
p_longyear = p.regex('20\d\d') | p.regex('19\d\d')
p_month = p.regex('10|11|12|0?[1-9]').parsecmap(padDigit)
p_day = p.regex('3[01]|[012]?\d').parsecmap(padDigit)

@p.generate
def p_date_ymd():
  y = yield p_longyear
  yield p.optional(p.regex('[-/]'))
  m = yield p_month
  yield p.optional(p.regex('[-/]'))
  d = yield p_day
  return(Date(month=m,day=d,year=y))

@p.generate
def p_date_mdy():
  m = yield p_month
  yield p.optional(p.regex('[-/]'))
  d = yield p_day
  yield p.optional(p.regex('[-/]'))
  y = yield p_longyear
  return(Date(month=m,day=d,year=y))

p_date = p_date_ymd | p_date_mdy
