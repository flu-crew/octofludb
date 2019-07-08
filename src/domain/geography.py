import re

STATE_NAME2ABBR = {
    "alaska": "AK",
    "alabama": "AL",
    "arkansas": "AR",
    "arizona": "AZ",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "district_of_columbia": "DC",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "iowa": "IA",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "massachusetts": "MA",
    "maryland": "MD",
    "maine": "ME",
    "michigan": "MI",
    "minnesota": "MN",
    "missouri": "MO",
    "mississippi": "MS",
    "montana": "MT",
    "north_carolina": "NC",
    "north_dakota": "ND",
    "nebraska": "NE",
    "new_hampshire": "NH",
    "new_jersey": "NJ",
    "new_mexico": "NM",
    "nevada": "NV",
    "new_york": "NY",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode_island": "RI",
    "south_carolina": "SC",
    "south_dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "virginia": "VA",
    "vermont": "VT",
    "washington": "WA",
    "wisconsin": "WI",
    "west_virginia": "WV",
    "wyoming": "WY",
    # some mispellings:
    "nebraksa": "NE",
    "minneosta": "MN",
    "missourri": "MI",
    "ilinois": "IL",
    "pennsyvania": "PA",
}
STATE_ABBR = set(STATE_NAME2ABBR.values())


def state_to_code(name):
    """ Get the two letter code from a state name. Return None on failure. """
    name = name.strip()
    if name.upper() in STATE_ABBR:
        return name.upper()
    name = name.lower().replace(" ", "_")
    if name in STATE_NAME2ABBR:
        return STATE_NAME2ABBR[name]
    else:
        return None


COUNTRY_3LETTER_CODES = {
    "afghanistan": "AFG",
    "aland_islands": "ALA",
    "albania": "ALB",
    "algeria": "DZA",
    "american_samoa": "ASM",
    "andorra": "AND",
    "angola": "AGO",
    "anguilla": "AIA",
    "antarctica": "ATA",
    "antigua_barbuda": "ATG",
    "argentina": "ARG",
    "armenia": "ARM",
    "aruba": "ABW",
    "australia": "AUS",
    "austria": "AUT",
    "azerbaijan": "AZE",
    "bahamas": "BHS",
    "bahrain": "BHR",
    "bangladesh": "BGD",
    "barbados": "BRB",
    "belarus": "BLR",
    "belgium": "BEL",
    "belize": "BLZ",
    "benin": "BEN",
    "bermuda": "BMU",
    "bhutan": "BTN",
    "bolivia": "BOL",
    "bonaire,_sint_eustatius_saba": "BES",
    "bonaire": "BES",
    "bosnia_herzegovina": "BIH",
    "botswana": "BWA",
    "bouvet_island": "BVT",
    "brazil": "BRA",
    "british_indian_ocean_territory": "IOT",
    "brunei_darussalam": "BRN",
    "bulgaria": "BGR",
    "burkina_faso": "BFA",
    "burundi": "BDI",
    "cambodia": "KHM",
    "cameroon": "CMR",
    "canada": "CAN",
    "cape_verde": "CPV",
    "cayman_islands": "CYM",
    "central_african_republic": "CAF",
    "chad": "TCD",
    "chile": "CHL",
    "china": "CHN",
    "christmas_island": "CXR",
    "cocos_islands": "CCK",
    "cocos_(keeling)_islands": "CCK",
    "colombia": "COL",
    "comoros": "COM",
    "congo": "COG",
    "republic_congo": "COG",
    "congo,_democratic_republic": "COD",
    "democratic_republic_congo": "COD",
    "dr_congo": "COD",
    "drc": "COD",
    "droc": "COD",
    "cook_islands": "COK",
    "costa_rica": "CRI",
    "cote_d'ivoire": "CIV",
    "cote_divoire": "CIV",
    "croatia": "HRV",
    "cuba": "CUB",
    "curaçao": "CUW",
    "cyprus": "CYP",
    "czechia": "CZE",
    "czech_republic": "CZE",
    "czechoslovakia": None,  # dissolved in 1993
    "denmark": "DNK",
    "djibouti": "DJI",
    "dominica": "DMA",
    "dominican_republic": "DOM",
    "ecuador": "ECU",
    "egypt": "EGY",
    "el_salvador": "SLV",
    "equatorial_guinea": "GNQ",
    "eritrea": "ERI",
    "estonia": "EST",
    "ethiopia": "ETH",
    "europe": None,
    "falkland_islands_(malvinas)": "FLK",
    "falkland_islands": "FLK",
    "faroe_islands": "FRO",
    "fiji": "FJI",
    "finland": "FIN",
    "france": "FRA",
    "french_guiana": "GUF",
    "french_polynesia": "PYF",
    "french_southern_territories": "ATF",
    "gabon": "GAB",
    "gambia": "GMB",
    "gaza_strip": None,
    "georgia": "GEO",
    "germany": "DEU",
    "ghana": "GHA",
    "gibraltar": "GIB",
    "greece": "GRC",
    "greenland": "GRL",
    "grenada": "GRD",
    "guadeloupe": "GLP",
    "guam": "GUM",
    "guatemala": "GTM",
    "guernsey": "GGY",
    "guinea": "GIN",
    "guinea-bissau": "GNB",
    "guyana": "GUY",
    "haiti": "HTI",
    "heard_mc_donald_islands": "HMD",
    "holy_see_(vatican_city_state)": "VAT",
    "vatican_city_state": "VAT",
    "vatican_city": "VAT",
    "honduras": "HND",
    "hong_kong": "HKG",
    "hungary": "HUN",
    "iceland": "ISL",
    "india": "IND",
    "indonesia": "IDN",
    "iran": "IRN",
    "iran,_islamic_republic": "IRN",
    "islamic_republic_iran": "IRN",
    "iraq": "IRQ",
    "ireland": "IRL",
    "isle_man": "IMN",
    "israel": "ISR",
    "italy": "ITA",
    "jamaica": "JAM",
    "japan": "JPN",
    "jersey": "JEY",
    "jordan": "JOR",
    "kazakhstan": "KAZ",
    "kenya": "KEN",
    "kiribati": "KIR",
    "north_korea": "PRK",
    "korea,_democratic_people's_republic": "PRK",
    "democratic_people's_republic_korea": "PRK",
    "south_korea": "KOR",
    "korea": "KOR",
    "republic_korea": "KOR",
    "kosovo": None,
    "kuwait": "KWT",
    "kyrgyzstan": "KGZ",
    "lab": None,
    "laos": "LAO",
    "lao_people's_democratic_republic": "LAO",
    "latvia": "LVA",
    "lebanon": "LBN",
    "lesotho": "LSO",
    "liberia": "LBR",
    "libya": "LBY",
    "state_libya": "LBY",
    "liechtenstein": "LIE",
    "lithuania": "LTU",
    "luxembourg": "LUX",
    "macao": "MAC",
    "macau": "MAC",
    "north_macedonia": "MKD",  # as of Feb 2019 through the ratification of the Prespa agreement,
    "madagascar": "MDG",
    "malawi": "MWI",
    "malaysia": "MYS",
    "maldives": "MDV",
    "mali": "MLI",
    "malta": "MLT",
    "marshall_islands": "MHL",
    "martinique": "MTQ",
    "mauritania": "MRT",
    "mauritius": "MUS",
    "mayotte": "MYT",
    "mexico": "MEX",
    "micronesia,_federated_states": "FSM",
    "federated_states_micronesia": "FSM",
    "micronesia": "FSM",
    "middle_east": None,
    "moldova": "MDA",
    "republic_moldova": "MDA",
    "monaco": "MCO",
    "mongolia": "MNG",
    "montenegro": "MNE",
    "montserrat": "MSR",
    "morocco": "MAR",
    "mozambique": "MOZ",
    "myanmar": "MMR",
    "namibia": "NAM",
    "nauru": "NRU",
    "nepal": "NPL",
    "netherlands": "NLD",
    "new_caledonia": "NCL",
    "new_zealand": "NZL",
    "nicaragua": "NIC",
    "niger": "NER",
    "nigeria": "NGA",
    "niue": "NIU",
    "norfolk_island": "NFK",
    "northern_mariana_islands": "MNP",
    "norway": "NOR",
    "oman": "OMN",
    "pakistan": "PAK",
    "palau": "PLW",
    "palestinian_territory,_occupied": "PSE",
    "occupied_palestinian_territory": "PSE",
    "palestine": "PSE",
    "state_palestine": "PSE",
    "panama": "PAN",
    "papua_new_guinea": "PNG",
    "paraguay": "PRY",
    "peru": "PER",
    "philippines": "PHL",
    "pitcairn": "PCN",
    "poland": "POL",
    "portugal": "PRT",
    "puerto_rico": "PRI",
    "qatar": "QAT",
    "republic_serbia": "SRB",
    "serbia": "SRB",
    "reunion": "REU",
    "romania": "ROU",
    "russia_federation": "RUS",
    "russia": "RUS",
    "ussr": "RUS",  # give or take a few countries,
    "rwanda": "RWA",
    "saint_barthélemy": "BLM",
    "saint_helena": "SHN",
    "saint_kitts_nevis": "KNA",
    "saint_lucia": "LCA",
    "saint_martin": "MAF",
    "saint_pierre_miquelon": "SPM",
    "saint_vincent_grenadines": "VCT",
    "samoa": "WSM",
    "san_marino": "SMR",
    "sao_tome_principe": "STP",
    "saudi_arabia": "SAU",
    "senegal": "SEN",
    "seychelles": "SYC",
    "sierra_leone": "SLE",
    "singapore": "SGP",
    "sint_maarten": "SXM",
    "slovakia": "SVK",
    "slovenia": "SVN",
    "solomon_islands": "SLB",
    "somalia": "SOM",
    "south_africa": "ZAF",
    "south_georgia_south_sandwich_islands": "SGS",
    "south_sudan": "SSD",
    "spain": "ESP",
    "sri_lanka": "LKA",
    "sudan": "SDN",
    "suriname": "SUR",
    "svalbard_jan_mayen": "SJM",
    "swaziland": "SWZ",
    "sweden": "SWE",
    "switzerland": "CHE",
    "syrian_arab_republic": "SYR",
    "syria": "SYR",
    "taiwan": "TWN",
    "tajikistan": "TJK",
    "tanzania,_united_republic": "TZA",
    "thailand": "THA",
    "timor-leste": "TLS",
    "togo": "TGO",
    "tokelau": "TKL",
    "tonga": "TON",
    "trinidad_tobago": "TTO",
    "tunisia": "TUN",
    "turkey": "TUR",
    "northern_cyprus": None,  # No, I don't recognize you either
    "turkmenistan": "TKM",
    "turks_caicos_islands": "TCA",
    "tuvalu": "TUV",
    "uganda": "UGA",
    "ukraine": "UKR",
    "united_arab_emirates": "ARE",
    "united_kingdom": "GBR",
    "united_states_minor_outlying_islands": "UMI",
    "united_states": "USA",
    "us": "USA",
    "united_states_of_america": "USA",
    "uruguay": "URY",
    "uzbekistan": "UZB",
    "vanuatu": "VUT",
    "venezuela": "VEN",
    "viet_nam": "VNM",
    "vietnam": "VNM",
    "virgin_islands,_british": "VGB",
    "british_virgin_islands": "VGB",
    "virgin_islands,_u.s.": "VIR",
    "u.s._virgin_islands": "VIR",
    "united_states_virgin_islands": "VIR",
    "us_virgin_islands": "VIR",
    "american_virgin_islands": "VIR",
    "wallis_futuna": "WLF",
    "west_bank": None,
    "western_sahara": "ESH",
    "yemen": "YEM",
    "zambia": "ZMB",
    "zimbabwe": "ZWE",
}
COUNTRY_NAMES = set(COUNTRY_3LETTER_CODES.keys())
COUNTRY_ABBREVIATIONS = set(COUNTRY_3LETTER_CODES.values())

clean_name = re.compile("of_|the_|and_|_of|_the|_and")


def country_to_code(name):
    """ Get the ISO 3-letter codes for a country. Return None on failure. """
    name = name.strip()
    if name.upper() in COUNTRY_ABBREVIATIONS:
        return name.upper()
    name = name.lower().strip().replace(" ", "_")
    name = clean_name.sub("", name)
    if name in COUNTRY_NAMES:
        return COUNTRY_3LETTER_CODES[name]
    else:
        return None
