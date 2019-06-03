import parsec as p
import re

STATE_ABBR = dict(
  AK = 'Alaska',
  AL = 'Alabama',
  AR = 'Arkansas',
  AZ = 'Arizona',
  CA = 'California',
  CO = 'Colorado',
  CT = 'Connecticut',
  DC = 'District Of Columbia',
  DE = 'Delaware',
  FL = 'Florida',
  GA = 'Georgia',
  HI = 'Hawaii',
  IA = 'Iowa',
  ID = 'Idaho',
  IL = 'Illinois',
  IN = 'Indiana',
  KS = 'Kansas',
  KY = 'Kentucky',
  LA = 'Louisiana',
  MA = 'Massachusetts',
  MD = 'Maryland',
  ME = 'Maine',
  MI = 'Michigan',
  MN = 'Minnesota',
  MO = 'Missouri',
  MS = 'Mississippi',
  MT = 'Montana',
  NC = 'North Carolina',
  ND = 'North Dakota',
  NE = 'Nebraska',
  NH = 'New Hampshire',
  NJ = 'New Jersey',
  NM = 'New Mexico',
  NV = 'Nevada',
  NY = 'New York',
  OH = 'Ohio',
  OK = 'Oklahoma',
  OR = 'Oregon',
  PA = 'Pennsylvania',
  RI = 'Rhode Island',
  SC = 'South Carolina',
  SD = 'South Dakota',
  TN = 'Tennessee',
  TX = 'Texas',
  UT = 'Utah',
  VA = 'Virginia',
  VT = 'Vermont',
  WA = 'Washington',
  WI = 'Wisconsin',
  WV = 'West Virginia',
  WY = 'Wyoming'
)

STATE_MISPELLINGS = dict(
  nebraksa    = "NE",
  minneosta   = "MN",
  missourri   = "MI",
  ilinois     = "IL",
  pennsyvania = "PA"
)

STATE_REGEX = re.compile('|'.join([s.replace(" ", "[ _]") for s in
    ( list(STATE_ABBR.values()) +
      list(STATE_ABBR.keys()) +
      list(STATE_MISPELLINGS.keys()) +
      ["USA", "United States"])
  ]), re.IGNORECASE)



p_state = p.regex(STATE_REGEX)
