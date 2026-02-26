"""
Database models for the Nigeria Election Results Platform.
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ─── Elections ────────────────────────────────────────────────────────────────

class Election(db.Model):
    __tablename__ = "elections"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    election_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="upcoming")  # upcoming/ongoing/completed

    election_types = db.relationship("ElectionType", backref="election", lazy=True,
                                     cascade="all, delete-orphan")


class ElectionType(db.Model):
    __tablename__ = "election_types"
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey("elections.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Presidential, Governorship, etc.
    slug = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(30), nullable=False)  # national/state/constituency/lga/ward

    candidates = db.relationship("Candidate", backref="election_type", lazy=True,
                                 cascade="all, delete-orphan")
    results = db.relationship("Result", backref="election_type", lazy=True,
                              cascade="all, delete-orphan")
    collation_results = db.relationship("CollationResult", backref="election_type", lazy=True,
                                        cascade="all, delete-orphan")


# ─── Geography ────────────────────────────────────────────────────────────────

class State(db.Model):
    __tablename__ = "states"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(5), unique=True, nullable=False)
    geo_zone = db.Column(db.String(30), nullable=False)

    lgas = db.relationship("LGA", backref="state", lazy=True)
    senatorial_districts = db.relationship("SenatorialDistrict", backref="state", lazy=True)
    federal_constituencies = db.relationship("FederalConstituency", backref="state", lazy=True)
    state_constituencies = db.relationship("StateConstituency", backref="state", lazy=True)


class SenatorialDistrict(db.Model):
    __tablename__ = "senatorial_districts"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey("states.id"), nullable=False)


class FederalConstituency(db.Model):
    __tablename__ = "federal_constituencies"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey("states.id"), nullable=False)
    senatorial_district_id = db.Column(db.Integer, db.ForeignKey("senatorial_districts.id"),
                                       nullable=True)


class StateConstituency(db.Model):
    __tablename__ = "state_constituencies"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey("states.id"), nullable=False)


class LGA(db.Model):
    __tablename__ = "lgas"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey("states.id"), nullable=False)
    federal_constituency_id = db.Column(db.Integer,
                                        db.ForeignKey("federal_constituencies.id"),
                                        nullable=True)

    wards = db.relationship("Ward", backref="lga", lazy=True)


class Ward(db.Model):
    __tablename__ = "wards"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    lga_id = db.Column(db.Integer, db.ForeignKey("lgas.id"), nullable=False)
    state_constituency_id = db.Column(db.Integer,
                                      db.ForeignKey("state_constituencies.id"),
                                      nullable=True)

    polling_units = db.relationship("PollingUnit", backref="ward", lazy=True)


class PollingUnit(db.Model):
    __tablename__ = "polling_units"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    code = db.Column(db.String(30), nullable=True)
    ward_id = db.Column(db.Integer, db.ForeignKey("wards.id"), nullable=False)
    registered_voters = db.Column(db.Integer, nullable=True)


# ─── Parties & Candidates ────────────────────────────────────────────────────

class Party(db.Model):
    __tablename__ = "parties"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    abbreviation = db.Column(db.String(10), unique=True, nullable=False)
    color = db.Column(db.String(10), default="#666666")

    candidates = db.relationship("Candidate", backref="party", lazy=True)


class Candidate(db.Model):
    __tablename__ = "candidates"
    id = db.Column(db.Integer, primary_key=True)
    election_type_id = db.Column(db.Integer, db.ForeignKey("election_types.id"), nullable=False)
    party_id = db.Column(db.Integer, db.ForeignKey("parties.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)

    # Geographic scope — only one set per candidate based on election level
    state_id = db.Column(db.Integer, db.ForeignKey("states.id"), nullable=True)
    senatorial_district_id = db.Column(db.Integer,
                                       db.ForeignKey("senatorial_districts.id"), nullable=True)
    federal_constituency_id = db.Column(db.Integer,
                                        db.ForeignKey("federal_constituencies.id"), nullable=True)
    state_constituency_id = db.Column(db.Integer,
                                      db.ForeignKey("state_constituencies.id"), nullable=True)
    lga_id = db.Column(db.Integer, db.ForeignKey("lgas.id"), nullable=True)
    ward_id = db.Column(db.Integer, db.ForeignKey("wards.id"), nullable=True)

    results = db.relationship("Result", backref="candidate", lazy=True)


# ─── Results ─────────────────────────────────────────────────────────────────

class Result(db.Model):
    __tablename__ = "results"
    id = db.Column(db.Integer, primary_key=True)
    election_type_id = db.Column(db.Integer, db.ForeignKey("election_types.id"), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False)
    party_id = db.Column(db.Integer, db.ForeignKey("parties.id"), nullable=False)

    # Geographic level of this result (lowest level available)
    polling_unit_id = db.Column(db.Integer, db.ForeignKey("polling_units.id"), nullable=True)
    ward_id = db.Column(db.Integer, db.ForeignKey("wards.id"), nullable=True)
    lga_id = db.Column(db.Integer, db.ForeignKey("lgas.id"), nullable=True)
    state_id = db.Column(db.Integer, db.ForeignKey("states.id"), nullable=True)

    votes = db.Column(db.Integer, nullable=False, default=0)
    is_collated = db.Column(db.Boolean, default=False)
    entered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    entered_by = db.Column(db.String(100), nullable=True)


class CollationResult(db.Model):
    __tablename__ = "collation_results"
    id = db.Column(db.Integer, primary_key=True)
    election_type_id = db.Column(db.Integer, db.ForeignKey("election_types.id"), nullable=False)
    level = db.Column(db.String(20), nullable=False)  # ward/lga/state/national

    # Geographic scope
    ward_id = db.Column(db.Integer, db.ForeignKey("wards.id"), nullable=True)
    lga_id = db.Column(db.Integer, db.ForeignKey("lgas.id"), nullable=True)
    state_id = db.Column(db.Integer, db.ForeignKey("states.id"), nullable=True)

    total_registered = db.Column(db.Integer, nullable=True)
    total_accredited = db.Column(db.Integer, nullable=True)
    total_valid_votes = db.Column(db.Integer, nullable=True)
    total_rejected = db.Column(db.Integer, nullable=True)
    total_votes_cast = db.Column(db.Integer, nullable=True)
    winner_candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=True)
    returning_officer = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default="pending")  # pending/declared
    notes = db.Column(db.Text, nullable=True)

    winner = db.relationship("Candidate", foreign_keys=[winner_candidate_id])
