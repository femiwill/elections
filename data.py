"""
FCT Area Council Election Results — February 21, 2026
Data sourced from: Daily Post, Idoma Voice, Premium Times, Sahara Reporters, Politics Nigeria
"""

RESULTS = {
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
        },
        "Karu Ward": {
            "Karu Site II Beside New NEPA": {"APC": 17, "ADC": 26},
            "Jikwoyi / ESU Palace Phase 1": {"APC": 96, "ADC": 9},
            "Opposite Faith Link Global Pharmacy": {"APC": 103, "ADC": 4},
            "UNG Ginar / Health Centre": {"APC": 48, "ADC": 8},
            "Kugbo Primary School": {"APC": 57, "ADC": 12},
            "UNG Pashe I / B.T.S. Karu": {"APC": 58, "ADC": 8},
            "UNG Hausawa II / Old Market Square": {"APC": 133, "ADC": 3},
        },
        "Nyanya Ward": {
            "Polling Unit 016 (Chairmanship)": {"APC": 13, "PDP": 1, "SDP": 2, "ADC": 5, "APGA": 1},
            "Polling Unit 016 (Councillorship)": {"APC": 11, "PDP": 1, "SDP": 0, "ADC": 4, "APGA": 1},
            "Polling Unit 091 (Chairmanship)": {"APC": 20, "PDP": 1, "ADC": 1, "BOOT": 1, "NNPP": 1},
            "Polling Unit 091 (Councillorship)": {"APC": 11, "PDP": 12, "BOOT": 1},
        },
        "Wuse Ward": {
            "SUEZ CLS In Front of Blk 14": {"APC": 44, "ADC": 6, "SDP": 1},
        },
        "Garki Ward": {
            "Polling Unit 076, Sani Abacha Estate": {"ADC": 7, "APC": 2},
            "Polling Unit 002 (Kofo Abayomi St, Presidential Villa)": {"APC": 24, "ADC": 5},
            "Presidential Villa / Police Affairs Commission": {"APC": 32, "ADC": 11, "PDP": 2},
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
    },
    "Kuje": {
        "Kuje Ward": {
            "Polling Unit 04, Prison Command (Chairmanship)": {"PDP": 22, "APC": 17, "ADC": 5},
            "Wowo Primary School, Unit 04 (Chairmanship)": {"PDP": 18, "APC": 10, "ADC": 6},  # PDP won per Daily Post
        },
    },
    "Kwali": {},
    "Gwagwalada": {},
    "Abaji": {},
}

# Election metadata
ELECTION_INFO = {
    "title": "FCT Area Council Election Results 2026",
    "date": "February 21, 2026",
    "description": "Results from the Federal Capital Territory Area Council Elections held on Saturday, February 21, 2026. "
                   "Voters across 6 area councils elected 6 chairmen and 62 councillors across 2,822 polling units.",
    "area_councils": ["AMAC", "Bwari", "Kuje", "Kwali", "Gwagwalada", "Abaji"],
    "total_polling_units": 2822,
    "registered_voters": 1580000,
    "positions": "6 Chairmanship + 62 Councillorship seats",
    "source_note": "Partial results from news reports. Official final results to be declared by INEC.",
}

# Party colors for display
PARTY_COLORS = {
    "APC": "#009401",    # Green
    "PDP": "#E3242B",    # Red
    "ADC": "#0066B3",    # Blue
    "LP": "#FF6B00",     # Orange
    "SDP": "#FFD700",    # Gold
    "APGA": "#800080",   # Purple
    "NNPP": "#DC143C",   # Crimson
    "ZLP": "#228B22",    # Forest green
    "YPP": "#FF1493",    # Deep pink
    "Accord": "#4169E1", # Royal blue
    "BOOT": "#8B4513",   # Saddle brown
    "AA": "#696969",     # Gray
    "ADP": "#2F4F4F",    # Dark slate
}
