"""
Nigeria Election Results — February 21, 2026
FCT Area Council Elections + Rivers & Kano State By-Elections
Data sourced from: INEC, Daily Post, Premium Times, Sahara Reporters, Politics Nigeria, TVC News, PM News, Idoma Voice, Channels TV
"""

# ══════════════════════════════════════════════════════════════════════════════
# FCT AREA COUNCIL ELECTION RESULTS
# ══════════════════════════════════════════════════════════════════════════════

FCT_RESULTS = {
    "AMAC": {
        "Gwarinpa Ward": {
            "DAPE": {"APC": 93, "ADC": 26},
            "Kuchigoro Primary School": {"APC": 126, "ADC": 12},
            "Kuchigoro Primary School III": {"APC": 54, "ADC": 8},
            "Gbagyi Dancing Ground": {"APC": 45, "ADC": 24},
            "Utako Primary School I": {"APC": 10, "ADC": 7},
            "Besides VIO Office Mabushi": {"APC": 29, "ADC": 16},
            "Kado Village II / Kado Raya Ung.": {"APC": 15, "ADC": 4},
            "Life Camp II / Market Gate": {"APC": 5, "ADC": 16},
            "Federal Staff Hospital by Setraco Gate": {"APC": 7, "ADC": 16},
            "Setraco Gate IV": {"APC": 0, "ADC": 15},
            "Staff Quarters Block": {"APC": 16, "ADC": 2},
            "LEA Primary School Kado Kuchi": {"APC": 45, "ADC": 24},
            "Jabi Primary School II": {"APC": 32, "ADC": 5},
            "Gwarimpa Magistrate Court": {"ADC": 8, "APC": 0, "PDP": 0},
            "PU 047, Gwarinpa": {"ADC": 29, "APC": 4, "SDP": 2},
            "Gwarinpa Village Playground": {"APC": 88, "ADC": 11},
        },
        "Karu Ward": {
            "Karu Site II Beside New NEPA": {"APC": 17, "ADC": 26},
            "Jikwoyi / ESU Palace Phase 1": {"APC": 96, "ADC": 9},
            "Opposite Faith Link Global Pharmacy": {"APC": 103, "ADC": 4},
            "UNG Ginar / Health Centre": {"APC": 48, "ADC": 8},
            "Kugbo Primary School": {"APC": 57, "ADC": 12},
            "UNG Pashe I / B.T.S. Karu": {"APC": 58, "ADC": 8},
            "UNG Hausawa II / Old Market Square": {"APC": 133, "ADC": 3},
            "Supreme Court Staff Quarters Karu": {"APC": 12, "ADC": 12},
        },
        "Nyanya Ward": {
            "Polling Unit 016 (Chairmanship)": {"APC": 13, "PDP": 1, "SDP": 2, "ADC": 5, "APGA": 1},
            "Polling Unit 016 (Councillorship)": {"APC": 11, "PDP": 1, "SDP": 0, "ADC": 4, "APGA": 1},
            "Polling Unit 091 (Chairmanship)": {"APC": 20, "PDP": 1, "ADC": 1, "BOOT": 1, "NNPP": 1},
            "Polling Unit 091 (Councillorship)": {"APC": 11, "PDP": 12, "BOOT": 1},
        },
        "Wuse Ward": {
            "SUEZ CLS In Front of Blk 14": {"APC": 44, "ADC": 6, "SDP": 1},
            "Polling Unit 076, Sani Abacha Estate": {"ADC": 7, "APC": 2},
        },
        "Garki Ward": {
            "PU 004, Garki Village 2 (Chairmanship)": {"APC": 229, "ADC": 15, "APGA": 1},
            "PU 004, Garki Village (Councillorship)": {"APC": 145, "YPP": 46, "ADC": 42},
            "PU 002, Kofo Abayomi St, Presidential Villa": {"APC": 24, "ADC": 5},
            "Presidential Villa / Police Affairs Commission": {"APC": 32, "ADC": 11, "PDP": 2},
            "PU 151, Garki": {"ADC": 5, "APC": 0, "PDP": 0},
        },
        "Kabusa Ward": {
            "PU 019, Govt Secondary School Tundu (Chairmanship)": {"APC": 41, "ADC": 8},
        },
        "Lugbe Ward": {
            "New Site Estate FHA Lugbe": {"ADC": 48, "APC": 7, "YPP": 1, "PRP": 1},
            "Area 2": {"ADC": 33, "APC": 30, "SDP": 4, "PRP": 2, "ZLP": 1},
            "LGEA Primary School Lugbe, Unit 098": {"ADC": 18, "ADP": 2, "APC": 1},
        },
    },
    "Bwari": {
        "Kubwa Ward": {
            "LEA Primary School Kubwa II, Unit 044 (Chairmanship)": {"ADC": 20, "APC": 7, "APGA": 3, "Accord": 1, "PDP": 1},
            "LEA Primary School Kubwa II, Unit 044 (Councillorship)": {"ADC": 14, "APC": 4, "PDP": 4, "APGA": 3, "ZLP": 3, "YPP": 2, "SDP": 1, "Accord": 1},
            "LEA Primary School Kubwa II, Unit 045 (Chairmanship)": {"ADC": 13, "APC": 11, "ZLP": 3, "APGA": 3, "PDP": 2, "Accord": 1, "AA": 1},
            "LEA Primary School Kubwa II, Unit 045 (Councillorship)": {"ADC": 10, "APC": 10, "ZLP": 5, "PDP": 4, "APGA": 2, "YPP": 2, "Accord": 1},
            "LEA Primary School Kubwa II, Unit 047 (Chairmanship)": {"ADC": 15, "APC": 2, "ZLP": 5, "APGA": 4, "SDP": 2, "PDP": 2},
            "LEA Primary School Kubwa II, Unit 047 (Councillorship)": {"ADC": 12, "ZLP": 10, "APGA": 4, "PDP": 3, "YPP": 1},
            "LEA Primary School Kubwa II, Unit 006 (Chairmanship)": {"APC": 20, "ADC": 19, "ZLP": 13, "APGA": 10, "PDP": 8, "Accord": 5, "SDP": 2, "ADP": 1},
            "LEA Primary School Kubwa II, Unit 006 (Councillorship)": {"APC": 20, "ZLP": 16, "YPP": 12, "APGA": 9, "ADC": 8, "Accord": 6, "SDP": 1, "ADP": 1},
        },
        "Ushafa Ward": {
            "PU 006, Ushafa (Chairmanship)": {"ZLP": 46, "APC": 36, "PDP": 10, "ADC": 5, "SDP": 1, "Accord": 1, "NNPP": 1},
            "PU 006, Ushafa (Councillorship)": {"PDP": 41, "APC": 36, "ZLP": 16, "SDP": 3, "ADC": 2, "APGA": 1, "Accord": 1},
            "PU 005, Bwari/Ushafa (Chairmanship)": {"ZLP": 33, "APC": 26, "PDP": 8, "APGA": 2, "ADC": 1, "SDP": 1},
            "PU 005, Bwari/Ushafa (Councillorship)": {"PDP": 28, "APC": 27, "ZLP": 14, "ADP": 3, "APGA": 1, "SDP": 1},
            "PU 007, Ushafa (Chairmanship)": {"ZLP": 41, "APC": 24, "PDP": 8, "ADC": 5, "APGA": 3, "Accord": 1},
            "PU 007, Ushafa (Councillorship)": {"PDP": 33, "APC": 28, "ZLP": 17, "ADC": 3, "APGA": 3},
        },
    },
    "Kuje": {
        "Kuje Ward": {
            "PU 04, Prison Command (Chairmanship)": {"PDP": 22, "APC": 17, "ADC": 5},
            "Wowo Primary School, PU 04 (Chairmanship)": {"PDP": 18, "APC": 10, "ADC": 6},
        },
    },
    "Kwali": {
        "Yangoji Ward": {
            "PU 008, Yangoji Primary School II (Chairmanship)": {"PDP": 17, "APC": 17, "ADP": 2},
            "PU 008, Yangoji Primary School II (Councillorship)": {"PDP": 19, "APC": 13, "ADP": 2},
        },
    },
    "Gwagwalada": {},
    "Abaji": {},
}

# Final Chairmanship Results (declared by INEC)
FCT_CHAIRMANSHIP_WINNERS = {
    "AMAC": {
        "winner": "Christopher Maikalangu", "party": "APC", "votes": None,
        "note": "Re-elected for 2nd term",
        "runner_up": "Dr. Moses Paul", "runner_up_party": "ADC", "runner_up_votes": None,
    },
    "Bwari": {
        "winner": "Musa Dikko", "party": "APC", "votes": 18066,
        "runner_up": "Andrew Gwani Igu", "runner_up_party": "PDP", "runner_up_votes": 13279,
    },
    "Kuje": {
        "winner": "Abdullahi D. Galadima", "party": "APC", "votes": 15175,
    },
    "Kwali": {
        "winner": "Joseph K. Shazin", "party": "APC", "votes": 15309,
    },
    "Gwagwalada": {
        "winner": "Danze Mustapha Adams", "party": "APGA", "votes": 15950,
    },
    "Abaji": {
        "winner": "Abdulrahaman Ajayi", "party": "APC", "votes": 13515,
        "runner_up": "Yahaya Garba", "runner_up_party": "PDP", "runner_up_votes": 10632,
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# RIVERS STATE BY-ELECTIONS
# ══════════════════════════════════════════════════════════════════════════════

RIVERS_BYELECTIONS = {
    "Ahoada East State Constituency II": {
        "type": "State House of Assembly By-Election",
        "date": "February 21, 2026",
        "returning_officer": "Prof. Rosemary Ogbo",
        "results": {
            "APC - Ukalikpe Napoleon": 3980,
            "AA - Ego Marvelous": 33,
        },
        "winner": "Ukalikpe Napoleon",
        "winner_party": "APC",
        "total_valid": 4013,
        "note": "PDP, LP, ADC did not field candidates",
    },
    "Khana State Constituency II": {
        "type": "State House of Assembly By-Election",
        "date": "February 21, 2026",
        "returning_officer": "Prof. Angela Briggs",
        "results": {
            "APC - Henrietta Bulabari": 7647,
            "ZLP": 47,
            "AA": 46,
            "NNPP": 37,
            "YPP": 23,
        },
        "winner": "Henrietta Bulabari",
        "winner_party": "APC",
        "registered_voters": 71914,
        "accredited": 7834,
        "total_valid": 7800,
        "rejected": 34,
        "note": "PDP, LP, ADC not on ballot",
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# KANO STATE BY-ELECTIONS
# ══════════════════════════════════════════════════════════════════════════════

KANO_BYELECTIONS = {
    "Kano Municipal State Constituency": {
        "type": "State House of Assembly By-Election",
        "date": "February 21, 2026",
        "results": {},
        "winner": None,
        "winner_party": None,
        "registered_voters": None,
        "note": "NNPP, PDP, ADC excluded from ballot by INEC. APC candidate Nabil Sarki Aliyu "
                "(son of deceased lawmaker Hon. Sarki Aliyu Daneji, who died Dec 24, 2025) contested. "
                "Low voter turnout attributed to Ramadan fasting. "
                "9 parties cleared: Accord, ADP, APP, AAC, APC, APM, PRP, YPP, ZLP. "
                "~535,000 registered voters across 1,014 polling units (both constituencies). "
                "Results awaiting official declaration.",
    },
    "Ungogo State Constituency": {
        "type": "State House of Assembly By-Election",
        "date": "February 21, 2026",
        "results": {},
        "winner": None,
        "winner_party": None,
        "registered_voters": None,
        "note": "NNPP, PDP, ADC excluded from ballot. APC candidate Aminu Sa'ad "
                "(son of deceased lawmaker Hon. Aminu Sa'adu Ungogo, who died Dec 24, 2025; "
                "defected from NNPP) contested. Low voter turnout. "
                "Results awaiting official declaration.",
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# METADATA & DISPLAY CONFIG
# ══════════════════════════════════════════════════════════════════════════════

ELECTION_INFO = {
    "title": "Nigeria Election Results — February 21, 2026",
    "date": "February 21, 2026",
    "description": "FCT Area Council Elections, Rivers & Kano State Assembly By-Elections",
    "fct": {
        "title": "FCT Area Council Elections",
        "area_councils": ["AMAC", "Bwari", "Kuje", "Kwali", "Gwagwalada", "Abaji"],
        "total_polling_units": 2822,
        "registered_voters": 1680315,
        "positions": "6 Chairmanship + 62 Councillorship seats",
        "summary": "APC won 5 of 6 chairmanship seats. APGA won Gwagwalada.",
    },
    "rivers": {
        "title": "Rivers State Assembly By-Elections",
        "constituencies": 2,
        "summary": "APC won both seats (Ahoada East II & Khana II). PDP/LP/ADC not on ballot.",
    },
    "kano": {
        "title": "Kano State Assembly By-Elections",
        "constituencies": 2,
        "summary": "2 seats contested. NNPP/PDP/ADC excluded from ballot. Low turnout reported.",
    },
    "source_note": "Data from news reports. Official results declared by INEC.",
}

PARTY_COLORS = {
    "APC": "#009401",
    "PDP": "#E3242B",
    "ADC": "#0066B3",
    "LP": "#FF6B00",
    "SDP": "#FFD700",
    "APGA": "#800080",
    "NNPP": "#DC143C",
    "ZLP": "#228B22",
    "YPP": "#FF1493",
    "Accord": "#4169E1",
    "BOOT": "#8B4513",
    "AA": "#696969",
    "ADP": "#2F4F4F",
    "AAC": "#FF4500",
    "APP": "#A0522D",
    "APM": "#6B8E23",
    "PRP": "#CD853F",
}
