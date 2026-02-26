"""
Migrate hardcoded election data from data.py into the database.

Usage:
    from migrate_legacy import migrate_legacy
    migrate_legacy()          # call inside an app context
"""
from datetime import date
from models import (
    db, Election, ElectionType, State, LGA, Ward, PollingUnit,
    Party, Candidate, Result, CollationResult, StateConstituency,
)
from data import (
    FCT_RESULTS, FCT_CHAIRMANSHIP_WINNERS,
    RIVERS_BYELECTIONS, KANO_BYELECTIONS,
    ELECTION_INFO, PARTY_COLORS,
)

# ── Mapping from data.py area-council keys to DB LGA names ────────────────────
AREA_COUNCIL_TO_LGA = {
    "AMAC": "Municipal Area Council (AMAC)",
    "Bwari": "Bwari",
    "Kuje": "Kuje",
    "Kwali": "Kwali",
    "Gwagwalada": "Gwagwalada",
    "Abaji": "Abaji",
}

# ── Full party names (best-effort) keyed by abbreviation ──────────────────────
PARTY_FULL_NAMES = {
    "APC": "All Progressives Congress",
    "PDP": "Peoples Democratic Party",
    "ADC": "African Democratic Congress",
    "LP": "Labour Party",
    "SDP": "Social Democratic Party",
    "APGA": "All Progressives Grand Alliance",
    "NNPP": "New Nigeria Peoples Party",
    "ZLP": "Zenith Labour Party",
    "YPP": "Young Progressives Party",
    "Accord": "Accord",
    "BOOT": "Boot Party",
    "AA": "Action Alliance",
    "ADP": "Action Democratic Party",
    "AAC": "African Action Congress",
    "APP": "Action Peoples Party",
    "APM": "Allied Peoples Movement",
    "PRP": "Peoples Redemption Party",
    "APN": "Action Peoples Network",
    "BP": "Boot Party",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

_party_cache: dict[str, Party] = {}


def _get_or_create_party(abbreviation: str) -> Party:
    """Return existing Party or create one (with colour from PARTY_COLORS)."""
    if abbreviation in _party_cache:
        return _party_cache[abbreviation]

    party = Party.query.filter_by(abbreviation=abbreviation).first()
    if party is None:
        party = Party(
            name=PARTY_FULL_NAMES.get(abbreviation, abbreviation),
            abbreviation=abbreviation,
            color=PARTY_COLORS.get(abbreviation, "#666666"),
        )
        db.session.add(party)
        db.session.flush()
    _party_cache[abbreviation] = party
    return party


def _get_or_create_ward(lga: LGA, ward_name: str) -> Ward:
    """Return existing Ward under the LGA or create one."""
    ward = Ward.query.filter_by(lga_id=lga.id, name=ward_name).first()
    if ward is None:
        ward = Ward(name=ward_name, lga_id=lga.id)
        db.session.add(ward)
        db.session.flush()
    return ward


def _get_or_create_polling_unit(ward: Ward, pu_name: str) -> PollingUnit:
    """Return existing PollingUnit under the Ward or create one."""
    pu = PollingUnit.query.filter_by(ward_id=ward.id, name=pu_name).first()
    if pu is None:
        pu = PollingUnit(name=pu_name, ward_id=ward.id)
        db.session.add(pu)
        db.session.flush()
    return pu


def _get_or_create_state_constituency(state: State, name: str) -> StateConstituency:
    """Return existing StateConstituency or create one."""
    sc = StateConstituency.query.filter_by(state_id=state.id, name=name).first()
    if sc is None:
        sc = StateConstituency(name=name, state_id=state.id)
        db.session.add(sc)
        db.session.flush()
    return sc


# ── Main migration ────────────────────────────────────────────────────────────

def migrate_legacy():
    """
    Migrate all hardcoded election data into the database.
    Idempotent — skips if the FCT election already exists.
    """
    _party_cache.clear()

    # ── 1. FCT Area Council Elections 2026 ────────────────────────────────
    fct_election = Election.query.filter_by(slug="fct-area-council-2026").first()
    if fct_election:
        print("[migrate_legacy] FCT election already exists — skipping.")
    else:
        fct_election = _migrate_fct()

    # ── 2. Rivers State Assembly By-Elections 2026 ────────────────────────
    rivers_election = Election.query.filter_by(slug="rivers-byelections-2026").first()
    if rivers_election:
        print("[migrate_legacy] Rivers by-election already exists — skipping.")
    else:
        _migrate_rivers()

    # ── 3. Kano State Assembly By-Elections 2026 ──────────────────────────
    kano_election = Election.query.filter_by(slug="kano-byelections-2026").first()
    if kano_election:
        print("[migrate_legacy] Kano by-election already exists — skipping.")
    else:
        _migrate_kano()

    # ── 4. Upcoming Elections ───────────────────────────────────────────
    _seed_upcoming_elections()

    db.session.commit()

    # ── 5. Import GPS coordinates ──────────────────────────────────────
    _import_gps_coordinates()

    print("[migrate_legacy] Migration complete.")


def _seed_upcoming_elections():
    """Seed upcoming Nigerian elections with their scheduled dates."""
    upcoming = [
        {
            "name": "Ekiti State Governorship Election 2026",
            "slug": "ekiti-governorship-2026",
            "date": date(2026, 6, 18),
            "status": "upcoming",
            "description": "Off-cycle governorship election in Ekiti State.",
            "types": [("Governorship", "governorship", "state")],
        },
        {
            "name": "Osun State Governorship Election 2026",
            "slug": "osun-governorship-2026",
            "date": date(2026, 9, 22),
            "status": "upcoming",
            "description": "Off-cycle governorship election in Osun State. Test run for the national platform.",
            "types": [("Governorship", "governorship", "state")],
        },
        {
            "name": "2027 General Elections",
            "slug": "2027-general-elections",
            "date": date(2027, 2, 18),
            "status": "upcoming",
            "description": "Nigeria's general elections — Presidential, Governorship, Senate, House of Representatives, and State Assembly across 36 states + FCT.",
            "types": [
                ("Presidential", "presidential", "national"),
                ("Governorship", "governorship", "state"),
                ("Senate", "senate", "constituency"),
                ("House of Representatives", "house-of-reps", "constituency"),
                ("State Assembly", "state-assembly", "constituency"),
            ],
        },
    ]

    for e in upcoming:
        if Election.query.filter_by(slug=e["slug"]).first():
            print(f"[migrate_legacy] {e['name']} already exists — skipping.")
            continue

        election = Election(
            name=e["name"],
            slug=e["slug"],
            election_date=e["date"],
            status=e["status"],
            description=e["description"],
        )
        db.session.add(election)
        db.session.flush()

        for type_name, type_slug, level in e["types"]:
            et = ElectionType(
                election_id=election.id,
                name=type_name,
                slug=type_slug,
                level=level,
            )
            db.session.add(et)

        db.session.flush()
        print(f"[migrate_legacy] {e['name']} created.")

    # ── Seed candidates for Ekiti & Osun governorship ────────────────────────
    _seed_governorship_candidates()


def _seed_governorship_candidates():
    """Seed major party candidates for upcoming governorship elections."""
    ekiti = State.query.filter_by(code="EK").first()
    osun = State.query.filter_by(code="OS").first()
    if not ekiti or not osun:
        return

    gov_candidates = {
        "ekiti-governorship-2026": [
            ("APC", "Biodun Oyebanji"),
            ("PDP", "Bisi Kolawole"),
            ("LP", "Reuben Famosaya"),
            ("NNPP", "Abejide Olumide"),
            ("SDP", "Segun Adekola"),
            ("ADC", "Wole Oluyede"),
            ("APGA", "Ayo Afolabi"),
            ("Accord", "Tunde Ogundipe"),
            ("YPP", "Femi Adeleye"),
            ("ZLP", "Joseph Akinbode"),
        ],
        "osun-governorship-2026": [
            ("APC", "Ademola Adeleke"),
            ("PDP", "Dotun Babayemi"),
            ("LP", "Lasun Yusuf"),
            ("NNPP", "Akin Ogunbiyi"),
            ("SDP", "Fatai Akinbade"),
            ("ADC", "Adekunle Oyelami"),
            ("APGA", "Oyegoke Olajide"),
            ("Accord", "Sola Adeyemo"),
            ("YPP", "Adebayo Omisore"),
            ("ZLP", "Kolapo Olusola"),
        ],
    }

    state_map = {
        "ekiti-governorship-2026": ekiti,
        "osun-governorship-2026": osun,
    }

    for slug, candidates in gov_candidates.items():
        election = Election.query.filter_by(slug=slug).first()
        if not election:
            continue
        gov_type = ElectionType.query.filter_by(
            election_id=election.id, slug="governorship"
        ).first()
        if not gov_type:
            continue

        state = state_map[slug]
        existing = Candidate.query.filter_by(election_type_id=gov_type.id).count()
        if existing > 0:
            print(f"[migrate_legacy] {election.name} already has {existing} candidates — skipping.")
            continue

        for abbr, name in candidates:
            party = Party.query.filter_by(abbreviation=abbr).first()
            if not party:
                continue
            db.session.add(Candidate(
                election_type_id=gov_type.id,
                party_id=party.id,
                name=name,
                state_id=state.id,
            ))

        db.session.flush()
        count = Candidate.query.filter_by(election_type_id=gov_type.id).count()
        print(f"[migrate_legacy] {election.name}: {count} candidates added.")


# ══════════════════════════════════════════════════════════════════════════════
# FCT
# ══════════════════════════════════════════════════════════════════════════════

def _migrate_fct():
    # Create election record
    fct_info = ELECTION_INFO["fct"]
    election = Election(
        name="FCT Area Council Elections 2026",
        slug="fct-area-council-2026",
        election_date=date(2026, 2, 21),
        status="completed",
        description=fct_info.get("summary", ""),
    )
    db.session.add(election)
    db.session.flush()

    # Create election types
    chairmanship_type = ElectionType(
        election_id=election.id,
        name="Chairmanship",
        slug="chairmanship",
        level="lga",
    )
    councillorship_type = ElectionType(
        election_id=election.id,
        name="Councillorship",
        slug="councillorship",
        level="ward",
    )
    db.session.add_all([chairmanship_type, councillorship_type])
    db.session.flush()

    # Get FCT state
    fct_state = State.query.filter_by(name="FCT").first()
    if fct_state is None:
        fct_state = State.query.filter_by(code="FC").first()
    if fct_state is None:
        fct_state = State.query.filter(State.name.ilike("%federal capital%")).first()
    if fct_state is None:
        raise RuntimeError(
            "FCT state not found in the database. "
            "Please run seed_data first to populate states and LGAs."
        )

    # Build LGA lookup: data key -> LGA model
    lga_lookup: dict[str, LGA] = {}
    for data_key, db_name in AREA_COUNCIL_TO_LGA.items():
        lga = LGA.query.filter_by(state_id=fct_state.id, name=db_name).first()
        if lga is None:
            # Fallback: try case-insensitive partial match
            lga = LGA.query.filter(
                LGA.state_id == fct_state.id,
                LGA.name.ilike(f"%{data_key}%"),
            ).first()
        if lga is None:
            print(f"[migrate_legacy] WARNING: LGA not found for '{data_key}' — creating it.")
            lga = LGA(name=db_name, state_id=fct_state.id)
            db.session.add(lga)
            db.session.flush()
        lga_lookup[data_key] = lga

    # ── 4. Polling-unit level results from FCT_RESULTS ────────────────────
    print("[migrate_legacy] Migrating FCT polling-unit results...")
    for ac_key, wards_data in FCT_RESULTS.items():
        lga = lga_lookup[ac_key]
        for ward_name, pus_data in wards_data.items():
            ward = _get_or_create_ward(lga, ward_name)
            for pu_name, party_votes in pus_data.items():
                pu = _get_or_create_polling_unit(ward, pu_name)

                # Determine if this PU is chairmanship or councillorship
                pu_lower = pu_name.lower()
                if "(councillorship)" in pu_lower:
                    etype = councillorship_type
                else:
                    # Default to chairmanship (most PU results are chairmanship)
                    etype = chairmanship_type

                for party_abbr, votes in party_votes.items():
                    party = _get_or_create_party(party_abbr)

                    # Create a generic candidate for PU-level results
                    candidate = Candidate(
                        election_type_id=etype.id,
                        party_id=party.id,
                        name=f"{party_abbr} Candidate — {ac_key}",
                        lga_id=lga.id,
                    )
                    db.session.add(candidate)
                    db.session.flush()

                    result = Result(
                        election_type_id=etype.id,
                        candidate_id=candidate.id,
                        party_id=party.id,
                        polling_unit_id=pu.id,
                        ward_id=ward.id,
                        lga_id=lga.id,
                        state_id=fct_state.id,
                        votes=votes,
                    )
                    db.session.add(result)

    db.session.flush()

    # ── 5. Chairmanship collation results from FCT_CHAIRMANSHIP_WINNERS ──
    print("[migrate_legacy] Migrating FCT chairmanship collation results...")
    for ac_key, data in FCT_CHAIRMANSHIP_WINNERS.items():
        lga = lga_lookup[ac_key]

        # Winner candidate
        winner_party = _get_or_create_party(data["party"])
        winner_candidate = Candidate(
            election_type_id=chairmanship_type.id,
            party_id=winner_party.id,
            name=data["winner"],
            lga_id=lga.id,
        )
        db.session.add(winner_candidate)
        db.session.flush()

        # Winner result (lga-level collated)
        winner_result = Result(
            election_type_id=chairmanship_type.id,
            candidate_id=winner_candidate.id,
            party_id=winner_party.id,
            lga_id=lga.id,
            state_id=fct_state.id,
            votes=data["votes"],
            is_collated=True,
        )
        db.session.add(winner_result)

        # Runner-up candidate
        runner_up_party = _get_or_create_party(data["runner_up_party"])
        runner_up_name = data.get("runner_up", f"{data['runner_up_party']} candidate")
        runner_up_candidate = Candidate(
            election_type_id=chairmanship_type.id,
            party_id=runner_up_party.id,
            name=runner_up_name,
            lga_id=lga.id,
        )
        db.session.add(runner_up_candidate)
        db.session.flush()

        # Runner-up result
        runner_up_votes = data.get("runner_up_votes")
        if runner_up_votes is not None:
            runner_up_result = Result(
                election_type_id=chairmanship_type.id,
                candidate_id=runner_up_candidate.id,
                party_id=runner_up_party.id,
                lga_id=lga.id,
                state_id=fct_state.id,
                votes=runner_up_votes,
                is_collated=True,
            )
            db.session.add(runner_up_result)

        # Build notes
        notes_parts = []
        if data.get("note"):
            notes_parts.append(data["note"])

        # CollationResult
        collation = CollationResult(
            election_type_id=chairmanship_type.id,
            level="lga",
            lga_id=lga.id,
            state_id=fct_state.id,
            total_registered=data.get("registered_voters"),
            total_accredited=data.get("accredited"),
            total_valid_votes=data.get("valid_votes"),
            total_rejected=data.get("rejected"),
            total_votes_cast=data.get("total_cast"),
            winner_candidate_id=winner_candidate.id,
            returning_officer=data.get("returning_officer"),
            status="declared",
            notes="; ".join(notes_parts) if notes_parts else None,
        )
        db.session.add(collation)

    db.session.flush()
    print(f"[migrate_legacy] FCT election created (id={election.id}).")
    return election


# ══════════════════════════════════════════════════════════════════════════════
# RIVERS STATE BY-ELECTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _migrate_rivers():
    rivers_info = ELECTION_INFO["rivers"]
    election = Election(
        name="Rivers State Assembly By-Elections 2026",
        slug="rivers-byelections-2026",
        election_date=date(2026, 2, 21),
        status="completed",
        description=rivers_info.get("summary", ""),
    )
    db.session.add(election)
    db.session.flush()

    state_assembly_type = ElectionType(
        election_id=election.id,
        name="State Assembly",
        slug="state-assembly",
        level="constituency",
    )
    db.session.add(state_assembly_type)
    db.session.flush()

    # Get Rivers state
    rivers_state = State.query.filter(State.name.ilike("%rivers%")).first()
    if rivers_state is None:
        raise RuntimeError(
            "Rivers state not found in the database. "
            "Please run seed_data first to populate states."
        )

    _migrate_byelection_constituencies(
        byelection_data=RIVERS_BYELECTIONS,
        election_type=state_assembly_type,
        state=rivers_state,
    )

    db.session.flush()
    print(f"[migrate_legacy] Rivers by-election created (id={election.id}).")


# ══════════════════════════════════════════════════════════════════════════════
# KANO STATE BY-ELECTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _migrate_kano():
    kano_info = ELECTION_INFO["kano"]
    election = Election(
        name="Kano State Assembly By-Elections 2026",
        slug="kano-byelections-2026",
        election_date=date(2026, 2, 21),
        status="completed",
        description=kano_info.get("summary", ""),
    )
    db.session.add(election)
    db.session.flush()

    state_assembly_type = ElectionType(
        election_id=election.id,
        name="State Assembly",
        slug="state-assembly",
        level="constituency",
    )
    db.session.add(state_assembly_type)
    db.session.flush()

    # Get Kano state
    kano_state = State.query.filter(State.name.ilike("%kano%")).first()
    if kano_state is None:
        raise RuntimeError(
            "Kano state not found in the database. "
            "Please run seed_data first to populate states."
        )

    _migrate_byelection_constituencies(
        byelection_data=KANO_BYELECTIONS,
        election_type=state_assembly_type,
        state=kano_state,
    )

    db.session.flush()
    print(f"[migrate_legacy] Kano by-election created (id={election.id}).")


# ══════════════════════════════════════════════════════════════════════════════
# Shared: State Assembly By-Election Constituencies
# ══════════════════════════════════════════════════════════════════════════════

def _migrate_byelection_constituencies(
    byelection_data: dict,
    election_type: ElectionType,
    state: State,
):
    """
    Migrate a RIVERS_BYELECTIONS or KANO_BYELECTIONS dict into the DB.

    Each key is a constituency name, and its value contains:
        results      — dict of "Party - Candidate Name": votes  (or "Party": votes)
        winner       — winner's name
        winner_party — winner's party abbreviation
        returning_officer, registered_voters, accredited, total_valid, rejected, note
    """
    for constituency_name, cdata in byelection_data.items():
        # Create or get the state constituency
        sc = _get_or_create_state_constituency(state, constituency_name)

        # Parse results and create candidates + collated results
        winner_candidate_obj = None

        for result_key, votes in cdata.get("results", {}).items():
            # result_key is either "PARTY - Candidate Name" or just "PARTY"
            if " - " in result_key:
                party_abbr, candidate_name = result_key.split(" - ", 1)
            else:
                party_abbr = result_key
                candidate_name = f"{result_key} Candidate — {constituency_name}"

            party = _get_or_create_party(party_abbr)

            candidate = Candidate(
                election_type_id=election_type.id,
                party_id=party.id,
                name=candidate_name,
                state_id=state.id,
                state_constituency_id=sc.id,
            )
            db.session.add(candidate)
            db.session.flush()

            # Store collated result at state level
            result = Result(
                election_type_id=election_type.id,
                candidate_id=candidate.id,
                party_id=party.id,
                state_id=state.id,
                votes=votes,
                is_collated=True,
            )
            db.session.add(result)

            # Identify the winner candidate
            if (cdata.get("winner") and candidate_name == cdata["winner"]):
                winner_candidate_obj = candidate
            elif (cdata.get("winner_party") == party_abbr and winner_candidate_obj is None
                  and candidate_name != f"{result_key} Candidate — {constituency_name}"):
                # Fallback: match by party if name didn't match exactly
                winner_candidate_obj = candidate

        db.session.flush()

        # If we still didn't find the winner candidate by name, try matching
        # the winner name against candidates we just created
        if winner_candidate_obj is None and cdata.get("winner"):
            winner_party = _get_or_create_party(cdata["winner_party"])
            winner_candidate_obj = Candidate.query.filter_by(
                election_type_id=election_type.id,
                name=cdata["winner"],
            ).first()
            # Last resort: create the winner candidate explicitly
            if winner_candidate_obj is None:
                winner_candidate_obj = Candidate(
                    election_type_id=election_type.id,
                    party_id=winner_party.id,
                    name=cdata["winner"],
                    state_id=state.id,
                    state_constituency_id=sc.id,
                )
                db.session.add(winner_candidate_obj)
                db.session.flush()

        # Build notes
        notes_parts = []
        if cdata.get("note"):
            notes_parts.append(cdata["note"])

        # CollationResult for this constituency
        collation = CollationResult(
            election_type_id=election_type.id,
            level="constituency",
            state_id=state.id,
            total_registered=cdata.get("registered_voters"),
            total_accredited=cdata.get("accredited"),
            total_valid_votes=cdata.get("total_valid"),
            total_rejected=cdata.get("rejected"),
            winner_candidate_id=winner_candidate_obj.id if winner_candidate_obj else None,
            returning_officer=cdata.get("returning_officer"),
            status="declared",
            notes="; ".join(notes_parts) if notes_parts else None,
        )
        db.session.add(collation)


def _import_gps_coordinates():
    """Import GPS coordinates from bundled CSV data into polling units."""
    import csv
    import re
    import os
    from collections import defaultdict

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "polling_units_gps.csv")
    if not os.path.exists(csv_path):
        print("[migrate_legacy] GPS CSV not found — skipping GPS import.")
        return

    # Check if any PUs already have coordinates
    has_coords = PollingUnit.query.filter(PollingUnit.latitude.isnot(None)).first()
    if has_coords:
        print("[migrate_legacy] GPS coordinates already imported — skipping.")
        return

    print("[migrate_legacy] Importing GPS coordinates...")

    STATE_MAP = {
        "ABIA": "Abia", "ADAMAWA": "Adamawa", "AKWA IBOM": "Akwa Ibom",
        "ANAMBRA": "Anambra", "BAUCHI": "Bauchi", "BAYELSA": "Bayelsa",
        "BENUE": "Benue", "BORNO": "Borno", "CROSS RIVER": "Cross River",
        "DELTA": "Delta", "EBONYI": "Ebonyi", "EDO": "Edo", "EKITI": "Ekiti",
        "ENUGU": "Enugu", "FEDERAL CAPITAL TERRITORY": "FCT", "GOMBE": "Gombe",
        "IMO": "Imo", "JIGAWA": "Jigawa", "KADUNA": "Kaduna", "KANO": "Kano",
        "KATSINA": "Katsina", "KEBBI": "Kebbi", "KOGI": "Kogi", "KWARA": "Kwara",
        "LAGOS": "Lagos", "NASARAWA": "Nasarawa", "NIGER": "Niger", "OGUN": "Ogun",
        "ONDO": "Ondo", "OSUN": "Osun", "OYO": "Oyo", "PLATEAU": "Plateau",
        "RIVERS": "Rivers", "SOKOTO": "Sokoto", "TARABA": "Taraba",
        "YOBE": "Yobe", "ZAMFARA": "Zamfara",
    }

    LGA_ALIASES = {
        ("Abia", "OBI NGWA"): "OBINGWA",
        ("Abia", "OSISIOMA NGWA"): "OSISIOMA",
        ("Abia", "UMU NNEOCHI"): "UMUNNEOCHI",
        ("Adamawa", "GAYUK"): "GUYUK",
        ("Adamawa", "GRIE"): "GIRE 1",
        ("Adamawa", "MAYO BELWA"): "MAYO BELWA",
        ("Anambra", "IHIALA"): "IHALA",
        ("Anambra", "ONITSHA SOUTH"): "ONITSHA SOUTH",
        ("Bauchi", "DAMBAN"): "DAMBAM",
        ("Borno", "MAIDUGURI"): "MAIDUGURI M. C.",
        ("Cross River", "CALABAR MUNICIPAL"): "CALABAR MUNICIPALITY",
        ("Edo", "UHUNMWONDE"): "UHUNMWODE",
        ("Gombe", "YAMALTU DEBA"): "YALMALTU DEBA",
        ("Jigawa", "BIRINIWA"): "BIRNIWA",
        ("Jigawa", "KIRI KASAMA"): "KIRIKA SAMMA",
        ("Kano", "DAMBATTA"): "DANBATA",
        ("Kano", "DAWAKIN KUDU"): "DAWAKI KUDU",
        ("Kano", "DAWAKIN TOFA"): "DAWAKI TOFA",
        ("Kano", "GARUN MALLAM"): "GARUN MALAM",
        ("Katsina", "MALUMFASHI"): "MALUFASHI",
        ("Kebbi", "ALEIRO"): "ALIERO",
        ("Kebbi", "AREWA DANDI"): "AREWA",
        ("Kogi", "KOTON KARFE"): "KOGI . K. K.",
        ("Kogi", "MOPA MURO"): "MOPA MORO",
        ("Kogi", "OGORI MAGONGO"): "OGORI MANGOGO",
        ("Kwara", "OKE ERO"): "OKE ERO",
        ("Kwara", "PATEGI"): "PATIGI",
        ("Lagos", "IFAKO IJAIYE"): "IFAKO IJAYE",
        ("Lagos", "SHOMOLU"): "SOMOLU",
        ("Ondo", "ILE OLUJI OKEIGBO"): "ILE OLUJI OKE IGBO",
        ("Osun", "AIYEDAADE"): "AYEDAADE",
        ("Osun", "AIYEDIRE"): "AYEDIRE",
        ("Osun", "ATAKUNMOSA EAST"): "ATAKUMOSA EAST",
        ("Osun", "ATAKUNMOSA WEST"): "ATAKUMOSA WEST",
        ("Oyo", "OGBOMOSHO NORTH"): "OGBOMOSO NORTH",
        ("Oyo", "OGBOMOSHO SOUTH"): "OGBOMOSO SOUTH",
        ("Oyo", "ORELOPE"): "OORELOPE",
    }

    def norm(name):
        name = name.upper().strip()
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r'\s*\(.*?\)', '', name)
        name = name.replace('/', ' ').replace('-', ' ')
        name = re.sub(r'\s+', ' ', name)
        return name.strip()

    # Build LGA centroids from CSV
    lga_coords = defaultdict(list)
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat_str = row.get('location.latitude', '').strip()
            lng_str = row.get('location.longitude', '').strip()
            if not lat_str or not lng_str:
                continue
            try:
                lat = float(lat_str)
                lng = float(lng_str)
            except ValueError:
                continue
            if not (3.0 < lat < 15.0 and 2.0 < lng < 16.0):
                continue
            csv_state = row['state_name'].strip()
            db_state = STATE_MAP.get(csv_state)
            if not db_state:
                continue
            lga_coords[(db_state, norm(row['local_government_name']))].append((lat, lng))

    centroids = {}
    for key, coords in lga_coords.items():
        avg_lat = sum(c[0] for c in coords) / len(coords)
        avg_lng = sum(c[1] for c in coords) / len(coords)
        centroids[key] = (avg_lat, avg_lng)

    csv_by_state = defaultdict(dict)
    for (cs, cl), val in centroids.items():
        csv_by_state[cs][cl] = val

    print(f"[migrate_legacy] GPS: {len(centroids)} LGA centroids built from CSV")

    # Match and update
    states = State.query.all()
    state_map = {s.name: s.id for s in states}
    total_pus = PollingUnit.query.count()
    print(f"[migrate_legacy] GPS: {len(states)} states, {total_pus} PUs in DB")
    updated = 0

    for state_name, state_id in state_map.items():
        lgas = LGA.query.filter_by(state_id=state_id).all()
        for lga in lgas:
            norm_lga = norm(lga.name)
            key = (state_name, norm_lga)

            centroid = centroids.get(key)
            if not centroid and key in LGA_ALIASES:
                centroid = centroids.get((state_name, norm(LGA_ALIASES[key])))
            if not centroid:
                clean_db = re.sub(r'[^A-Z0-9]', '', norm_lga)
                for cl, val in csv_by_state.get(state_name, {}).items():
                    if re.sub(r'[^A-Z0-9]', '', cl) == clean_db:
                        centroid = val
                        break

            if centroid:
                lat, lng = centroid
                wards = Ward.query.filter_by(lga_id=lga.id).all()
                for ward in wards:
                    pus = PollingUnit.query.filter_by(ward_id=ward.id).filter(
                        PollingUnit.latitude.is_(None)
                    ).all()
                    for pu in pus:
                        pu.latitude = lat
                        pu.longitude = lng
                        updated += 1

    db.session.commit()
    print(f"[migrate_legacy] GPS coordinates imported for {updated:,} polling units.")


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os

    # Allow running standalone: python migrate_legacy.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from app import app  # noqa: E402

    with app.app_context():
        db.create_all()
        migrate_legacy()
