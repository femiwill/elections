"""
Nigeria Election Results Platform — app.py
Multi-election, database-driven results tracker.
"""
import os
import csv
import io
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, jsonify, request, redirect, url_for,
    session, flash, abort, Response
)
from datetime import timezone
from models import (
    db, Election, ElectionType, State, LGA, Ward, PollingUnit,
    Party, Candidate, Result, CollationResult
)

# ══════════════════════════════════════════════════════════════════════════════
# APP CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'elections-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///elections.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'elections-admin-2026')
db.init_app(app)


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION — auto-seed + auto-migrate on first run
# ══════════════════════════════════════════════════════════════════════════════

with app.app_context():
    db.create_all()
    # Seed geographic data + parties if tables are empty
    if State.query.count() == 0:
        from seed_data import seed
        seed()
    # Migrate legacy flat-file data into normalised tables
    if Election.query.count() == 0:
        from migrate_legacy import migrate_legacy
        migrate_legacy()
    # Seed wards + polling units for all LGAs if not yet populated
    if Ward.query.count() < 100:
        from seed_wards_pus import seed_wards_and_pus
        seed_wards_and_pus()
    # Import GPS coordinates for polling units (after all PUs exist)
    if PollingUnit.query.filter(PollingUnit.latitude.isnot(None)).count() == 0:
        from migrate_legacy import _import_gps_coordinates
        _import_gps_coordinates()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_party_colors_cache = None


def get_party_colors():
    """Return {abbreviation: color} dict from Party table, cached after first call."""
    global _party_colors_cache
    if _party_colors_cache is None:
        parties = Party.query.all()
        _party_colors_cache = {p.abbreviation: p.color for p in parties}
    return _party_colors_cache


def invalidate_party_colors_cache():
    """Clear the party-colors cache (call after party edits)."""
    global _party_colors_cache
    _party_colors_cache = None


def get_results_summary(election_type_id, level, geo_id):
    """
    Aggregate results for an election type at a given geographic level.

    level: 'national' | 'state' | 'lga' | 'ward' | 'polling_unit'
    geo_id: the id of the geographic entity (ignored for national)

    Returns a list of dicts:
        [{'party_id': .., 'abbreviation': .., 'color': .., 'total_votes': ..}, ...]
    sorted descending by total_votes.
    """
    q = db.session.query(
        Result.party_id,
        Party.abbreviation,
        Party.color,
        db.func.sum(Result.votes).label('total_votes')
    ).join(Party, Party.id == Result.party_id).filter(
        Result.election_type_id == election_type_id
    )

    if level == 'state' and geo_id:
        q = q.filter(Result.state_id == geo_id)
    elif level == 'lga' and geo_id:
        q = q.filter(Result.lga_id == geo_id)
    elif level == 'ward' and geo_id:
        q = q.filter(Result.ward_id == geo_id)
    elif level == 'polling_unit' and geo_id:
        q = q.filter(Result.polling_unit_id == geo_id)
    # 'national' — no geographic filter

    rows = q.group_by(Result.party_id, Party.abbreviation, Party.color) \
            .order_by(db.func.sum(Result.votes).desc()).all()

    return [
        {
            'party_id': r.party_id,
            'abbreviation': r.abbreviation,
            'color': r.color,
            'total_votes': int(r.total_votes or 0),
        }
        for r in rows
    ]


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE CONTEXT PROCESSOR
# ══════════════════════════════════════════════════════════════════════════════

@app.context_processor
def inject_globals():
    return {
        'party_colors': get_party_colors(),
        'all_elections': Election.query.order_by(Election.election_date.desc()).all(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN AUTH
# ══════════════════════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            flash('Please log in to access the admin panel.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == app.config['ADMIN_PASSWORD']:
            session['admin'] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Incorrect password.', 'danger')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Logged out.', 'info')
    return redirect(url_for('index'))


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/admin')
@login_required
def admin_dashboard():
    total_elections = Election.query.count()
    total_results = Result.query.count()
    total_parties = Party.query.count()
    total_candidates = Candidate.query.count()
    total_collations = CollationResult.query.count()
    elections = Election.query.order_by(Election.election_date.desc()).all()
    return render_template(
        'admin/dashboard.html',
        total_elections=total_elections,
        total_results=total_results,
        total_parties=total_parties,
        total_candidates=total_candidates,
        total_collations=total_collations,
        elections=elections,
    )


# ── Election CRUD ─────────────────────────────────────────────────────────────

@app.route('/admin/elections', methods=['GET', 'POST'])
@login_required
def admin_elections():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip()
        date_str = request.form.get('election_date', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'upcoming').strip()

        if not name or not slug:
            flash('Name and slug are required.', 'danger')
        elif Election.query.filter_by(slug=slug).first():
            flash('An election with that slug already exists.', 'danger')
        else:
            election = Election(
                name=name, slug=slug, description=description, status=status,
                election_date=datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None,
            )
            db.session.add(election)
            db.session.commit()
            flash(f'Election "{name}" created.', 'success')
            return redirect(url_for('admin_elections'))

    elections = Election.query.order_by(Election.election_date.desc()).all()
    return render_template('admin/elections.html', elections=elections)


@app.route('/admin/elections/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def admin_election_edit(id):
    election = Election.query.get_or_404(id)
    if request.method == 'POST':
        election.name = request.form.get('name', election.name).strip()
        election.slug = request.form.get('slug', election.slug).strip()
        date_str = request.form.get('election_date', '').strip()
        election.election_date = (
            datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else election.election_date
        )
        election.description = request.form.get('description', '').strip()
        election.status = request.form.get('status', election.status).strip()
        db.session.commit()
        flash(f'Election "{election.name}" updated.', 'success')
        return redirect(url_for('admin_elections'))
    return render_template('admin/election_edit.html', election=election)


@app.route('/admin/elections/<int:id>/delete', methods=['POST'])
@login_required
def admin_election_delete(id):
    election = Election.query.get_or_404(id)
    name = election.name
    db.session.delete(election)
    db.session.commit()
    flash(f'Election "{name}" deleted.', 'success')
    return redirect(url_for('admin_elections'))


# ── Election Types ────────────────────────────────────────────────────────────

@app.route('/admin/elections/<int:id>/types', methods=['GET', 'POST'])
@login_required
def admin_election_types(id):
    election = Election.query.get_or_404(id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip()
        level = request.form.get('level', 'national').strip()
        if not name or not slug:
            flash('Name and slug are required.', 'danger')
        else:
            et = ElectionType(election_id=election.id, name=name, slug=slug, level=level)
            db.session.add(et)
            db.session.commit()
            flash(f'Election type "{name}" added.', 'success')
            return redirect(url_for('admin_election_types', id=election.id))
    return render_template('admin/election_types.html', election=election)


# ── Candidates ────────────────────────────────────────────────────────────────

@app.route('/admin/elections/<int:id>/candidates', methods=['GET', 'POST'])
@login_required
def admin_candidates(id):
    election = Election.query.get_or_404(id)
    if request.method == 'POST':
        election_type_id = request.form.get('election_type_id', type=int)
        party_id = request.form.get('party_id', type=int)
        name = request.form.get('name', '').strip()
        state_id = request.form.get('state_id', type=int) or None
        senatorial_district_id = request.form.get('senatorial_district_id', type=int) or None
        federal_constituency_id = request.form.get('federal_constituency_id', type=int) or None
        state_constituency_id = request.form.get('state_constituency_id', type=int) or None
        lga_id = request.form.get('lga_id', type=int) or None
        ward_id = request.form.get('ward_id', type=int) or None

        if not election_type_id or not party_id or not name:
            flash('Election type, party and name are required.', 'danger')
        else:
            candidate = Candidate(
                election_type_id=election_type_id,
                party_id=party_id,
                name=name,
                state_id=state_id,
                senatorial_district_id=senatorial_district_id,
                federal_constituency_id=federal_constituency_id,
                state_constituency_id=state_constituency_id,
                lga_id=lga_id,
                ward_id=ward_id,
            )
            db.session.add(candidate)
            db.session.commit()
            flash(f'Candidate "{name}" added.', 'success')
            return redirect(url_for('admin_candidates', id=election.id))

    parties = Party.query.order_by(Party.abbreviation).all()
    candidates = Candidate.query.join(ElectionType).filter(
        ElectionType.election_id == election.id
    ).order_by(ElectionType.id, Candidate.name).all()
    return render_template(
        'admin/candidates.html',
        election=election, parties=parties, candidates=candidates,
    )


# ── Result Entry ──────────────────────────────────────────────────────────────

@app.route('/admin/results/enter', methods=['GET', 'POST'])
@login_required
def admin_results_enter():
    elections = Election.query.order_by(Election.election_date.desc()).all()
    parties = Party.query.order_by(Party.abbreviation).all()
    return render_template('admin/results_enter.html', elections=elections, parties=parties)


@app.route('/admin/results/save', methods=['POST'])
@login_required
def admin_results_save():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON body provided'}), 400

    election_type_id = data.get('election_type_id')
    polling_unit_id = data.get('polling_unit_id') or None
    ward_id = data.get('ward_id') or None
    lga_id = data.get('lga_id') or None
    state_id = data.get('state_id') or None
    results_list = data.get('results', [])

    if not election_type_id or not results_list:
        return jsonify({'error': 'election_type_id and results list are required'}), 400

    # Resolve state_id from geographic hierarchy if not provided
    if not state_id:
        if polling_unit_id:
            pu = PollingUnit.query.get(polling_unit_id)
            if pu:
                ward = Ward.query.get(pu.ward_id)
                if ward:
                    lga_obj = LGA.query.get(ward.lga_id)
                    if lga_obj:
                        state_id = lga_obj.state_id
                    if not lga_id:
                        lga_id = ward.lga_id
                    if not ward_id:
                        ward_id = ward.id
        elif ward_id:
            ward = Ward.query.get(ward_id)
            if ward:
                lga_obj = LGA.query.get(ward.lga_id)
                if lga_obj:
                    state_id = lga_obj.state_id
                if not lga_id:
                    lga_id = ward.lga_id
        elif lga_id:
            lga_obj = LGA.query.get(lga_id)
            if lga_obj:
                state_id = lga_obj.state_id

    saved_count = 0
    for item in results_list:
        party_id = item.get('party_id')
        votes = item.get('votes', 0)
        if not party_id:
            continue

        # Find or create the candidate stub for this party + election_type
        candidate = Candidate.query.filter_by(
            election_type_id=election_type_id, party_id=party_id
        ).first()
        if not candidate:
            party = Party.query.get(party_id)
            candidate = Candidate(
                election_type_id=election_type_id,
                party_id=party_id,
                name=f'{party.abbreviation} Candidate' if party else 'Unknown',
                state_id=state_id,
            )
            db.session.add(candidate)
            db.session.flush()

        # Check for existing result at same geographic level
        existing = Result.query.filter_by(
            election_type_id=election_type_id,
            party_id=party_id,
            polling_unit_id=polling_unit_id,
            ward_id=ward_id,
            lga_id=lga_id,
            state_id=state_id,
        ).first()
        if existing:
            existing.votes = votes
        else:
            result = Result(
                election_type_id=election_type_id,
                candidate_id=candidate.id,
                party_id=party_id,
                polling_unit_id=polling_unit_id,
                ward_id=ward_id,
                lga_id=lga_id,
                state_id=state_id,
                votes=votes,
            )
            db.session.add(result)
        saved_count += 1

    db.session.commit()
    return jsonify({'success': True, 'saved': saved_count})


# ── Bulk CSV Upload ───────────────────────────────────────────────────────────

@app.route('/admin/results/bulk-upload', methods=['GET', 'POST'])
@login_required
def admin_results_bulk_upload():
    elections = Election.query.order_by(Election.election_date.desc()).all()
    if request.method == 'POST':
        election_type_id = request.form.get('election_type_id', type=int)
        csv_file = request.files.get('csv_file')

        if not election_type_id or not csv_file:
            flash('Election type and CSV file are required.', 'danger')
            return redirect(url_for('admin_results_bulk_upload'))

        try:
            stream = io.TextIOWrapper(csv_file.stream, encoding='utf-8-sig')
            reader = csv.DictReader(stream)
            saved = 0

            for row in reader:
                party_abbr = row.get('party', '').strip()
                votes = int(row.get('votes', 0))
                pu_code = row.get('polling_unit_code', '').strip()
                ward_name = row.get('ward', '').strip()
                lga_name = row.get('lga', '').strip()
                state_code = row.get('state', '').strip()

                party = Party.query.filter_by(abbreviation=party_abbr).first()
                if not party:
                    continue

                state = State.query.filter_by(code=state_code).first() if state_code else None
                state_id = state.id if state else None

                lga = None
                if lga_name and state_id:
                    lga = LGA.query.filter_by(name=lga_name, state_id=state_id).first()
                lga_id = lga.id if lga else None

                ward = None
                if ward_name and lga_id:
                    ward = Ward.query.filter_by(name=ward_name, lga_id=lga_id).first()
                ward_id = ward.id if ward else None

                pu = None
                if pu_code and ward_id:
                    pu = PollingUnit.query.filter_by(code=pu_code, ward_id=ward_id).first()
                polling_unit_id = pu.id if pu else None

                candidate = Candidate.query.filter_by(
                    election_type_id=election_type_id, party_id=party.id
                ).first()
                if not candidate:
                    candidate = Candidate(
                        election_type_id=election_type_id,
                        party_id=party.id,
                        name=f'{party.abbreviation} Candidate',
                        state_id=state_id,
                    )
                    db.session.add(candidate)
                    db.session.flush()

                result = Result(
                    election_type_id=election_type_id,
                    candidate_id=candidate.id,
                    party_id=party.id,
                    polling_unit_id=polling_unit_id,
                    ward_id=ward_id,
                    lga_id=lga_id,
                    state_id=state_id,
                    votes=votes,
                )
                db.session.add(result)
                saved += 1

            db.session.commit()
            flash(f'Successfully uploaded {saved} result rows.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'CSV upload error: {str(e)}', 'danger')

        return redirect(url_for('admin_results_bulk_upload'))

    return render_template('admin/bulk_upload.html', elections=elections)


# ── GPS Coordinates Upload ────────────────────────────────────────────────────

@app.route('/admin/coordinates', methods=['GET', 'POST'])
@login_required
def admin_coordinates():
    message = None
    if request.method == 'POST':
        csv_file = request.files.get('csv_file')
        if not csv_file:
            flash('No file uploaded.', 'danger')
            return redirect(url_for('admin_coordinates'))

        try:
            content = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
            updated = 0
            skipped = 0
            for row in reader:
                pu_code = (row.get('pu_code') or row.get('code') or '').strip()
                pu_id = row.get('pu_id') or row.get('id') or ''
                lat = row.get('latitude') or row.get('lat') or ''
                lng = row.get('longitude') or row.get('lng') or row.get('lon') or ''
                if not lat or not lng:
                    skipped += 1
                    continue
                try:
                    lat_f = float(lat)
                    lng_f = float(lng)
                except (ValueError, TypeError):
                    skipped += 1
                    continue

                pu = None
                if pu_id:
                    pu = PollingUnit.query.get(int(pu_id))
                if not pu and pu_code:
                    pu = PollingUnit.query.filter_by(code=pu_code).first()
                if pu:
                    pu.latitude = lat_f
                    pu.longitude = lng_f
                    updated += 1
                else:
                    skipped += 1

            db.session.commit()
            flash(f'Updated coordinates for {updated} polling units. {skipped} skipped.', 'success')
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')

        return redirect(url_for('admin_coordinates'))

    total_pus = PollingUnit.query.count()
    pus_with_coords = PollingUnit.query.filter(
        PollingUnit.latitude.isnot(None),
        PollingUnit.longitude.isnot(None),
    ).count()
    return render_template('admin/coordinates.html',
                           total_pus=total_pus,
                           pus_with_coords=pus_with_coords)


# ── Collation Declaration ─────────────────────────────────────────────────────

@app.route('/admin/results/declare', methods=['GET', 'POST'])
@login_required
def admin_results_declare():
    elections = Election.query.order_by(Election.election_date.desc()).all()
    if request.method == 'POST':
        election_type_id = request.form.get('election_type_id', type=int)
        level = request.form.get('level', '').strip()
        state_id = request.form.get('state_id', type=int) or None
        lga_id = request.form.get('lga_id', type=int) or None
        ward_id = request.form.get('ward_id', type=int) or None
        winner_candidate_id = request.form.get('winner_candidate_id', type=int) or None
        returning_officer = request.form.get('returning_officer', '').strip()
        total_registered = request.form.get('total_registered', type=int) or None
        total_accredited = request.form.get('total_accredited', type=int) or None
        total_valid_votes = request.form.get('total_valid_votes', type=int) or None
        total_rejected = request.form.get('total_rejected', type=int) or None
        total_votes_cast = request.form.get('total_votes_cast', type=int) or None
        notes = request.form.get('notes', '').strip()
        status = request.form.get('status', 'declared').strip()

        if not election_type_id or not level:
            flash('Election type and level are required.', 'danger')
        else:
            collation = CollationResult(
                election_type_id=election_type_id,
                level=level,
                state_id=state_id,
                lga_id=lga_id,
                ward_id=ward_id,
                winner_candidate_id=winner_candidate_id,
                returning_officer=returning_officer or None,
                total_registered=total_registered,
                total_accredited=total_accredited,
                total_valid_votes=total_valid_votes,
                total_rejected=total_rejected,
                total_votes_cast=total_votes_cast,
                notes=notes or None,
                status=status,
            )
            db.session.add(collation)
            db.session.commit()
            flash('Collation result declared.', 'success')
            return redirect(url_for('admin_results_declare'))

    collations = CollationResult.query.order_by(CollationResult.id.desc()).limit(50).all()
    return render_template(
        'admin/declare.html',
        elections=elections, collations=collations,
    )


# ══════════════════════════════════════════════════════════════════════════════
# AJAX API FOR ADMIN CASCADING DROPDOWNS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/states')
def api_states():
    states = State.query.order_by(State.name).all()
    return jsonify([{'id': s.id, 'name': s.name, 'code': s.code} for s in states])


@app.route('/api/lgas/<int:state_id>')
def api_lgas(state_id):
    lgas = LGA.query.filter_by(state_id=state_id).order_by(LGA.name).all()
    return jsonify([{'id': l.id, 'name': l.name} for l in lgas])


@app.route('/api/wards/<int:lga_id>')
def api_wards(lga_id):
    wards = Ward.query.filter_by(lga_id=lga_id).order_by(Ward.name).all()
    return jsonify([{'id': w.id, 'name': w.name} for w in wards])


@app.route('/api/polling-units/<int:ward_id>')
def api_polling_units(ward_id):
    pus = PollingUnit.query.filter_by(ward_id=ward_id).order_by(PollingUnit.name).all()
    return jsonify([{
        'id': p.id, 'name': p.name, 'code': p.code,
        'latitude': p.latitude, 'longitude': p.longitude,
    } for p in pus])


@app.route('/api/election-types/<int:election_id>')
def api_election_types(election_id):
    types = ElectionType.query.filter_by(election_id=election_id).order_by(ElectionType.name).all()
    return jsonify([{'id': t.id, 'name': t.name, 'slug': t.slug, 'level': t.level} for t in types])


@app.route('/api/candidates/<int:election_type_id>')
def api_candidates(election_type_id):
    candidates = Candidate.query.filter_by(election_type_id=election_type_id) \
                                .order_by(Candidate.name).all()
    return jsonify([
        {
            'id': c.id,
            'name': c.name,
            'party_id': c.party_id,
            'party': c.party.abbreviation if c.party else None,
        }
        for c in candidates
    ])


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════════════════════
# GEOGRAPHIC BROWSE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/states/<state_code>')
def state_browse(state_code):
    state = State.query.filter_by(code=state_code).first_or_404()
    lgas = LGA.query.filter_by(state_id=state.id).order_by(LGA.name).all()

    lga_data = []
    for lga in lgas:
        ward_count = Ward.query.filter_by(lga_id=lga.id).count()
        pu_count = PollingUnit.query.join(Ward).filter(Ward.lga_id == lga.id).count()
        lga_data.append({
            'lga': lga,
            'ward_count': ward_count,
            'pu_count': pu_count,
        })

    # Find elections relevant to this state (state-level + national)
    state_elections = []
    state_name_lower = state.name.replace(' State', '').lower()
    for election in Election.query.order_by(Election.election_date.desc()).all():
        matched = False
        # Match by election name (e.g. "FCT" in "FCT Area Council", "Rivers" in "Rivers State Assembly")
        if state_name_lower in election.name.lower():
            matched = True
        if not matched:
            for et in election.election_types:
                # National elections apply to all states
                if et.level == 'national':
                    matched = True
                    break
                # Check if any candidates or results are scoped to this state
                if Candidate.query.filter_by(election_type_id=et.id, state_id=state.id).first():
                    matched = True
                    break
                if Result.query.filter_by(election_type_id=et.id, state_id=state.id).first():
                    matched = True
                    break
        if matched:
            state_elections.append(election)

    return render_template('state_browse.html',
                           state=state,
                           lga_data=lga_data,
                           state_elections=state_elections)


@app.route('/states/<state_code>/lga/<int:lga_id>')
def lga_browse(state_code, lga_id):
    state = State.query.filter_by(code=state_code).first_or_404()
    lga = LGA.query.get_or_404(lga_id)
    if lga.state_id != state.id:
        abort(404)

    wards = Ward.query.filter_by(lga_id=lga.id).order_by(Ward.name).all()
    ward_data = []
    for ward in wards:
        pus = PollingUnit.query.filter_by(ward_id=ward.id).order_by(PollingUnit.name).all()
        ward_data.append({
            'ward': ward,
            'polling_units': pus,
        })

    return render_template('lga_browse.html',
                           state=state,
                           lga=lga,
                           ward_data=ward_data)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    # Split elections by status
    upcoming = Election.query.filter_by(status='upcoming').order_by(Election.election_date.asc()).all()
    completed = Election.query.filter(Election.status.in_(['completed', 'ongoing'])).order_by(Election.election_date.desc()).all()
    all_elections = Election.query.all()

    # All states grouped by geo zone, with LGA + PU counts
    states = State.query.order_by(State.name).all()
    geo_zones = {}
    state_info = {}
    for s in states:
        geo_zones.setdefault(s.geo_zone, []).append(s)
        lga_count = LGA.query.filter_by(state_id=s.id).count()
        pu_count = PollingUnit.query.join(Ward).join(LGA).filter(LGA.state_id == s.id).count()
        state_info[s.id] = {'lga_count': lga_count, 'pu_count': pu_count}

    total_results = Result.query.count()
    total_parties = Party.query.count()

    return render_template('index.html',
                           upcoming_elections=upcoming,
                           completed_elections=completed,
                           elections=all_elections,
                           states=states,
                           geo_zones=geo_zones,
                           state_info=state_info,
                           total_results=total_results,
                           total_parties=total_parties)


@app.route('/find-polling-unit')
def find_polling_unit():
    states = State.query.order_by(State.name).all()
    total_pus = PollingUnit.query.count()
    total_wards = Ward.query.count()
    return render_template('find_polling_unit.html',
                           states=states,
                           total_pus=total_pus,
                           total_wards=total_wards)


@app.route('/election/<slug>')
def election_overview(slug):
    election = Election.query.filter_by(slug=slug).first_or_404()
    election_types = ElectionType.query.filter_by(election_id=election.id).all()

    if not election_types:
        return render_template(
            'election.html', election=election, election_types=[],
            current_type=None, state_summaries=[], national_summary=[],
        )

    # Determine which election type is selected
    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = election_types[0]

    # National summary (all parties, total votes)
    national_summary = get_results_summary(selected_type.id, 'national', None)

    # State-level summaries
    state_results = db.session.query(
        Result.state_id,
        State.name,
        State.code,
        db.func.sum(Result.votes).label('total_votes'),
    ).join(State, State.id == Result.state_id).filter(
        Result.election_type_id == selected_type.id,
        Result.state_id.isnot(None),
    ).group_by(Result.state_id, State.name, State.code).all()

    state_summaries = []
    for sr in state_results:
        # Get leading party for this state
        party_results = get_results_summary(selected_type.id, 'state', sr.state_id)
        leading = party_results[0] if party_results else None

        # Count PUs reporting
        pus_reporting = Result.query.filter(
            Result.election_type_id == selected_type.id,
            Result.state_id == sr.state_id,
            Result.polling_unit_id.isnot(None),
        ).with_entities(Result.polling_unit_id).distinct().count()

        total_pus = PollingUnit.query.join(Ward).join(LGA).filter(
            LGA.state_id == sr.state_id
        ).count()

        pct_reporting = round(pus_reporting / total_pus * 100, 1) if total_pus > 0 else 0

        state_summaries.append({
            'state_id': sr.state_id,
            'state_name': sr.name,
            'state_code': sr.code,
            'total_votes': int(sr.total_votes or 0),
            'leading_party': leading['abbreviation'] if leading else None,
            'leading_color': leading['color'] if leading else '#666',
            'leading_votes': leading['total_votes'] if leading else 0,
            'pus_reporting': pus_reporting,
            'total_pus': total_pus,
            'pct_reporting': pct_reporting,
            'party_results': party_results,
        })

    # Sort by total votes descending
    state_summaries.sort(key=lambda x: x['total_votes'], reverse=True)

    # Get collation results (declared winners) for this election type
    collation_results = CollationResult.query.filter_by(
        election_type_id=selected_type.id,
        status='declared',
    ).all()

    # Build geo_items for the template (states or LGAs depending on level)
    geo_items = []
    for ss in state_summaries:
        geo_items.append({
            'name': ss['state_name'],
            'url': url_for('state_page', slug=slug, state_code=ss['state_code']),
            'leading_party': ss['leading_party'],
            'leading_color': ss['leading_color'],
            'total_votes': ss['total_votes'],
            'pct_reporting': ss['pct_reporting'],
        })

    # National totals for dashboard
    total_national_votes = sum(s['total_votes'] for s in national_summary)
    states_reporting = len(state_summaries)
    total_states = State.query.count()
    total_pus_reporting = sum(ss['pus_reporting'] for ss in state_summaries)
    total_pus_all = sum(ss['total_pus'] for ss in state_summaries) or PollingUnit.query.count()
    national_pct_reporting = round(total_pus_reporting / total_pus_all * 100, 1) if total_pus_all > 0 else 0

    # Latest result update timestamp
    latest_result = db.session.query(db.func.max(Result.entered_at)).filter(
        Result.election_type_id == selected_type.id
    ).scalar()

    return render_template(
        'election.html',
        election=election,
        election_types=election_types,
        current_type=selected_type,
        state_summaries=state_summaries,
        national_summary=national_summary,
        collation_results=collation_results,
        geo_items=geo_items,
        total_national_votes=total_national_votes,
        states_reporting=states_reporting,
        total_states=total_states,
        total_pus_reporting=total_pus_reporting,
        total_pus_all=total_pus_all,
        national_pct_reporting=national_pct_reporting,
        latest_result=latest_result,
    )


@app.route('/election/<slug>/<state_code>')
def state_page(slug, state_code):
    election = Election.query.filter_by(slug=slug).first_or_404()
    state = State.query.filter_by(code=state_code).first_or_404()

    election_types = ElectionType.query.filter_by(election_id=election.id).all()
    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type and election_types:
        selected_type = election_types[0]

    lga_summaries = []
    state_party_summary = []
    collation = None

    if selected_type:
        # State-wide party summary
        state_party_summary = get_results_summary(selected_type.id, 'state', state.id)

        # LGA-level summaries
        lga_results = db.session.query(
            Result.lga_id,
            LGA.name,
            db.func.sum(Result.votes).label('total_votes'),
        ).join(LGA, LGA.id == Result.lga_id).filter(
            Result.election_type_id == selected_type.id,
            Result.state_id == state.id,
            Result.lga_id.isnot(None),
        ).group_by(Result.lga_id, LGA.name).all()

        for lr in lga_results:
            party_results = get_results_summary(selected_type.id, 'lga', lr.lga_id)
            leading = party_results[0] if party_results else None
            lga_summaries.append({
                'lga_id': lr.lga_id,
                'lga_name': lr.name,
                'total_votes': int(lr.total_votes or 0),
                'leading_party': leading['abbreviation'] if leading else None,
                'leading_color': leading['color'] if leading else '#666',
                'leading_votes': leading['total_votes'] if leading else 0,
                'party_results': party_results,
            })
        lga_summaries.sort(key=lambda x: x['total_votes'], reverse=True)

        # Check for collation at state level
        collation = CollationResult.query.filter_by(
            election_type_id=selected_type.id,
            level='state',
            state_id=state.id,
        ).first()

    # Build party_totals as list of (abbreviation, total_votes) tuples for chart
    party_totals = [(p['abbreviation'], p['total_votes']) for p in state_party_summary]

    # Build lga_items for template: objects with .lga, .leading_party, etc.
    class LGAItem:
        def __init__(self, lga, leading_party, leading_color, total_votes):
            self.lga = lga
            self.leading_party = leading_party
            self.leading_color = leading_color
            self.total_votes = total_votes

    lga_items = []
    for ls in lga_summaries:
        lga_obj = LGA.query.get(ls['lga_id'])
        if lga_obj:
            lga_items.append(LGAItem(
                lga=lga_obj,
                leading_party=ls['leading_party'],
                leading_color=ls['leading_color'],
                total_votes=ls['total_votes'],
            ))

    # Reporting progress for state page
    total_lgas_in_state = LGA.query.filter_by(state_id=state.id).count()
    lgas_reporting = len(lga_summaries)
    pus_reporting_state = 0
    total_pus_state = 0
    if selected_type:
        pus_reporting_state = Result.query.filter(
            Result.election_type_id == selected_type.id,
            Result.state_id == state.id,
            Result.polling_unit_id.isnot(None),
        ).with_entities(Result.polling_unit_id).distinct().count()
        total_pus_state = PollingUnit.query.join(Ward).join(LGA).filter(
            LGA.state_id == state.id
        ).count()
    state_pct_reporting = round(pus_reporting_state / total_pus_state * 100, 1) if total_pus_state > 0 else 0

    return render_template(
        'state.html',
        election=election,
        state=state,
        election_types=election_types,
        current_type=selected_type,
        lga_items=lga_items,
        party_totals=party_totals,
        collation=collation,
        lgas_reporting=lgas_reporting,
        total_lgas_in_state=total_lgas_in_state,
        pus_reporting=pus_reporting_state,
        total_pus=total_pus_state,
        pct_reporting=state_pct_reporting,
    )


@app.route('/election/<slug>/<state_code>/<int:lga_id>')
def lga_page(slug, state_code, lga_id):
    election = Election.query.filter_by(slug=slug).first_or_404()
    state = State.query.filter_by(code=state_code).first_or_404()
    lga = LGA.query.get_or_404(lga_id)
    if lga.state_id != state.id:
        abort(404)

    election_types = ElectionType.query.filter_by(election_id=election.id).all()
    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type and election_types:
        selected_type = election_types[0]

    ward_summaries = []
    lga_party_summary = []

    if selected_type:
        lga_party_summary = get_results_summary(selected_type.id, 'lga', lga.id)

        ward_results = db.session.query(
            Result.ward_id,
            Ward.name,
            db.func.sum(Result.votes).label('total_votes'),
        ).join(Ward, Ward.id == Result.ward_id).filter(
            Result.election_type_id == selected_type.id,
            Result.lga_id == lga.id,
            Result.ward_id.isnot(None),
        ).group_by(Result.ward_id, Ward.name).all()

        for wr in ward_results:
            party_results = get_results_summary(selected_type.id, 'ward', wr.ward_id)
            leading = party_results[0] if party_results else None
            ward_summaries.append({
                'ward_id': wr.ward_id,
                'ward_name': wr.name,
                'total_votes': int(wr.total_votes or 0),
                'leading_party': leading['abbreviation'] if leading else None,
                'leading_color': leading['color'] if leading else '#666',
                'leading_votes': leading['total_votes'] if leading else 0,
                'party_results': party_results,
            })
        ward_summaries.sort(key=lambda x: x['total_votes'], reverse=True)

    party_totals = [(p['abbreviation'], p['total_votes']) for p in lga_party_summary]

    class WardItem:
        def __init__(self, ward, leading_party, leading_color, total_votes, pu_count):
            self.ward = ward
            self.leading_party = leading_party
            self.leading_color = leading_color
            self.total_votes = total_votes
            self.pu_count = pu_count

    ward_items = []
    for ws in ward_summaries:
        ward_obj = Ward.query.get(ws['ward_id'])
        if ward_obj:
            pu_count = PollingUnit.query.filter_by(ward_id=ward_obj.id).count()
            ward_items.append(WardItem(
                ward=ward_obj,
                leading_party=ws['leading_party'],
                leading_color=ws['leading_color'],
                total_votes=ws['total_votes'],
                pu_count=pu_count,
            ))

    # Check for collation at LGA level
    collation = None
    if selected_type:
        collation = CollationResult.query.filter_by(
            election_type_id=selected_type.id,
            level='lga',
            lga_id=lga.id,
        ).first()

    # Reporting progress for LGA page
    total_wards_in_lga = Ward.query.filter_by(lga_id=lga.id).count()
    wards_reporting = len(ward_summaries)
    pus_reporting_lga = 0
    total_pus_lga = 0
    if selected_type:
        pus_reporting_lga = Result.query.filter(
            Result.election_type_id == selected_type.id,
            Result.lga_id == lga.id,
            Result.polling_unit_id.isnot(None),
        ).with_entities(Result.polling_unit_id).distinct().count()
        total_pus_lga = PollingUnit.query.join(Ward).filter(
            Ward.lga_id == lga.id
        ).count()
    lga_pct_reporting = round(pus_reporting_lga / total_pus_lga * 100, 1) if total_pus_lga > 0 else 0

    return render_template(
        'lga.html',
        election=election,
        state=state,
        lga=lga,
        election_types=election_types,
        current_type=selected_type,
        ward_items=ward_items,
        party_totals=party_totals,
        collation=collation,
        wards_reporting=wards_reporting,
        total_wards_in_lga=total_wards_in_lga,
        pus_reporting=pus_reporting_lga,
        total_pus=total_pus_lga,
        pct_reporting=lga_pct_reporting,
    )


@app.route('/election/<slug>/<state_code>/<int:lga_id>/<int:ward_id>')
def ward_page(slug, state_code, lga_id, ward_id):
    election = Election.query.filter_by(slug=slug).first_or_404()
    state = State.query.filter_by(code=state_code).first_or_404()
    lga = LGA.query.get_or_404(lga_id)
    ward = Ward.query.get_or_404(ward_id)
    if lga.state_id != state.id or ward.lga_id != lga.id:
        abort(404)

    election_types = ElectionType.query.filter_by(election_id=election.id).all()
    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type and election_types:
        selected_type = election_types[0]

    pu_results = []
    ward_party_summary = []

    if selected_type:
        ward_party_summary = get_results_summary(selected_type.id, 'ward', ward.id)

        # Get all PUs in this ward that have results
        pus_with_results = db.session.query(
            Result.polling_unit_id,
            PollingUnit.name.label('pu_name'),
            PollingUnit.code.label('pu_code'),
        ).join(PollingUnit, PollingUnit.id == Result.polling_unit_id).filter(
            Result.election_type_id == selected_type.id,
            Result.ward_id == ward.id,
            Result.polling_unit_id.isnot(None),
        ).distinct().all()

        for pu_row in pus_with_results:
            party_results = get_results_summary(
                selected_type.id, 'polling_unit', pu_row.polling_unit_id
            )
            pu_results.append({
                'polling_unit_id': pu_row.polling_unit_id,
                'pu_name': pu_row.pu_name,
                'pu_code': pu_row.pu_code,
                'party_results': party_results,
                'total_votes': sum(p['total_votes'] for p in party_results),
            })
        pu_results.sort(key=lambda x: x['total_votes'], reverse=True)

    class PUItem:
        def __init__(self, pu, party_results, total_votes):
            self.pu = pu
            self.party_results = party_results  # list of (abbreviation, votes) tuples
            self.total_votes = total_votes

    pu_items = []
    for pr in pu_results:
        pu_obj = PollingUnit.query.get(pr['polling_unit_id'])
        if pu_obj:
            # Convert party_results dicts to (abbreviation, votes) tuples
            party_tuples = [(p['abbreviation'], p['total_votes']) for p in pr['party_results']]
            pu_items.append(PUItem(
                pu=pu_obj,
                party_results=party_tuples,
                total_votes=pr['total_votes'],
            ))

    # Ward reporting progress
    total_pus_in_ward = PollingUnit.query.filter_by(ward_id=ward.id).count()
    pus_with_data = len(pu_results)
    ward_pct_reporting = round(pus_with_data / total_pus_in_ward * 100, 1) if total_pus_in_ward > 0 else 0

    return render_template(
        'ward.html',
        election=election,
        state=state,
        lga=lga,
        ward=ward,
        election_types=election_types,
        current_type=selected_type,
        pu_items=pu_items,
        pus_reporting=pus_with_data,
        total_pus=total_pus_in_ward,
        pct_reporting=ward_pct_reporting,
    )


# ══════════════════════════════════════════════════════════════════════════════
# JSON API ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/elections')
def api_elections():
    elections = Election.query.order_by(Election.election_date.desc()).all()
    return jsonify([
        {
            'id': e.id,
            'name': e.name,
            'slug': e.slug,
            'election_date': e.election_date.isoformat() if e.election_date else None,
            'status': e.status,
            'description': e.description,
            'types': [
                {'id': t.id, 'name': t.name, 'slug': t.slug, 'level': t.level}
                for t in e.election_types
            ],
        }
        for e in elections
    ])


@app.route('/api/election/<slug>/summary')
def api_election_summary(slug):
    election = Election.query.filter_by(slug=slug).first_or_404()
    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()

    if not selected_type:
        return jsonify({'election': election.name, 'summary': []})

    summary = get_results_summary(selected_type.id, 'national', None)
    total_votes = sum(s['total_votes'] for s in summary)

    return jsonify({
        'election': election.name,
        'election_type': selected_type.name,
        'total_votes': total_votes,
        'summary': [
            {
                'party': s['abbreviation'],
                'color': s['color'],
                'votes': s['total_votes'],
                'percentage': round(s['total_votes'] / total_votes * 100, 2) if total_votes > 0 else 0,
            }
            for s in summary
        ],
    })


@app.route('/api/election/<slug>/state/<code>')
def api_election_state(slug, code):
    election = Election.query.filter_by(slug=slug).first_or_404()
    state = State.query.filter_by(code=code).first_or_404()

    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()

    if not selected_type:
        return jsonify({'state': state.name, 'results': []})

    summary = get_results_summary(selected_type.id, 'state', state.id)
    total_votes = sum(s['total_votes'] for s in summary)

    # Collation info
    collation = CollationResult.query.filter_by(
        election_type_id=selected_type.id, level='state', state_id=state.id
    ).first()

    return jsonify({
        'state': state.name,
        'state_code': state.code,
        'election_type': selected_type.name,
        'total_votes': total_votes,
        'collation': {
            'status': collation.status,
            'winner': collation.winner.name if collation and collation.winner else None,
            'returning_officer': collation.returning_officer if collation else None,
            'total_valid_votes': collation.total_valid_votes if collation else None,
            'total_rejected': collation.total_rejected if collation else None,
        } if collation else None,
        'results': [
            {
                'party': s['abbreviation'],
                'color': s['color'],
                'votes': s['total_votes'],
                'percentage': round(s['total_votes'] / total_votes * 100, 2) if total_votes > 0 else 0,
            }
            for s in summary
        ],
    })


@app.route('/api/election/<slug>/state/<code>/lgas')
def api_election_state_lgas(slug, code):
    election = Election.query.filter_by(slug=slug).first_or_404()
    state = State.query.filter_by(code=code).first_or_404()

    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()

    if not selected_type:
        return jsonify({'state': state.name, 'lgas': []})

    lga_results = db.session.query(
        Result.lga_id,
        LGA.name,
        db.func.sum(Result.votes).label('total_votes'),
    ).join(LGA, LGA.id == Result.lga_id).filter(
        Result.election_type_id == selected_type.id,
        Result.state_id == state.id,
        Result.lga_id.isnot(None),
    ).group_by(Result.lga_id, LGA.name).all()

    lgas = []
    for lr in lga_results:
        party_results = get_results_summary(selected_type.id, 'lga', lr.lga_id)
        leading = party_results[0] if party_results else None
        lgas.append({
            'lga_id': lr.lga_id,
            'lga_name': lr.name,
            'total_votes': int(lr.total_votes or 0),
            'leading_party': leading['abbreviation'] if leading else None,
            'results': [
                {'party': p['abbreviation'], 'color': p['color'], 'votes': p['total_votes']}
                for p in party_results
            ],
        })
    lgas.sort(key=lambda x: x['total_votes'], reverse=True)

    return jsonify({'state': state.name, 'state_code': state.code, 'lgas': lgas})


@app.route('/api/election/<slug>/lga/<int:id>/wards')
def api_election_lga_wards(slug, id):
    election = Election.query.filter_by(slug=slug).first_or_404()
    lga = LGA.query.get_or_404(id)

    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()

    if not selected_type:
        return jsonify({'lga': lga.name, 'wards': []})

    ward_results = db.session.query(
        Result.ward_id,
        Ward.name,
        db.func.sum(Result.votes).label('total_votes'),
    ).join(Ward, Ward.id == Result.ward_id).filter(
        Result.election_type_id == selected_type.id,
        Result.lga_id == lga.id,
        Result.ward_id.isnot(None),
    ).group_by(Result.ward_id, Ward.name).all()

    wards = []
    for wr in ward_results:
        party_results = get_results_summary(selected_type.id, 'ward', wr.ward_id)
        leading = party_results[0] if party_results else None
        wards.append({
            'ward_id': wr.ward_id,
            'ward_name': wr.name,
            'total_votes': int(wr.total_votes or 0),
            'leading_party': leading['abbreviation'] if leading else None,
            'results': [
                {'party': p['abbreviation'], 'color': p['color'], 'votes': p['total_votes']}
                for p in party_results
            ],
        })
    wards.sort(key=lambda x: x['total_votes'], reverse=True)

    return jsonify({'lga': lga.name, 'wards': wards})


@app.route('/api/election/<slug>/ward/<int:id>/pus')
def api_election_ward_pus(slug, id):
    election = Election.query.filter_by(slug=slug).first_or_404()
    ward = Ward.query.get_or_404(id)

    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()

    if not selected_type:
        return jsonify({'ward': ward.name, 'polling_units': []})

    pus_with_results = db.session.query(
        Result.polling_unit_id,
        PollingUnit.name.label('pu_name'),
        PollingUnit.code.label('pu_code'),
    ).join(PollingUnit, PollingUnit.id == Result.polling_unit_id).filter(
        Result.election_type_id == selected_type.id,
        Result.ward_id == ward.id,
        Result.polling_unit_id.isnot(None),
    ).distinct().all()

    pus = []
    for pu_row in pus_with_results:
        party_results = get_results_summary(
            selected_type.id, 'polling_unit', pu_row.polling_unit_id
        )
        pus.append({
            'polling_unit_id': pu_row.polling_unit_id,
            'name': pu_row.pu_name,
            'code': pu_row.pu_code,
            'results': [
                {'party': p['abbreviation'], 'color': p['color'], 'votes': p['total_votes']}
                for p in party_results
            ],
            'total_votes': sum(p['total_votes'] for p in party_results),
        })
    pus.sort(key=lambda x: x['total_votes'], reverse=True)

    return jsonify({'ward': ward.name, 'polling_units': pus})


# ── Search ────────────────────────────────────────────────────────────────────

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    election_slug = request.args.get('election', '').strip()

    if not q or len(q) < 2:
        return jsonify({'results': []})

    results = []
    search_term = f'%{q}%'

    # Search candidates
    candidate_query = Candidate.query.join(Party).join(ElectionType).join(Election)
    if election_slug:
        candidate_query = candidate_query.filter(Election.slug == election_slug)
    candidates = candidate_query.filter(
        db.or_(
            Candidate.name.ilike(search_term),
            Party.abbreviation.ilike(search_term),
            Party.name.ilike(search_term),
        )
    ).limit(20).all()

    for c in candidates:
        results.append({
            'type': 'candidate',
            'name': c.name,
            'party': c.party.abbreviation if c.party else None,
            'election_type': c.election_type.name if c.election_type else None,
            'election': c.election_type.election.name if c.election_type and c.election_type.election else None,
            'election_slug': c.election_type.election.slug if c.election_type and c.election_type.election else None,
        })

    # Search states
    states = State.query.filter(
        db.or_(State.name.ilike(search_term), State.code.ilike(search_term))
    ).limit(10).all()
    for s in states:
        results.append({
            'type': 'state',
            'name': s.name,
            'code': s.code,
        })

    # Search LGAs
    lgas = LGA.query.join(State).filter(LGA.name.ilike(search_term)).limit(10).all()
    for l in lgas:
        results.append({
            'type': 'lga',
            'name': l.name,
            'state': l.state.name if l.state else None,
            'state_code': l.state.code if l.state else None,
            'lga_id': l.id,
        })

    # Search wards
    wards = Ward.query.join(LGA).join(State).filter(
        Ward.name.ilike(search_term)
    ).limit(10).all()
    for w in wards:
        results.append({
            'type': 'ward',
            'name': w.name,
            'lga': w.lga.name if w.lga else None,
            'state': w.lga.state.name if w.lga and w.lga.state else None,
            'state_code': w.lga.state.code if w.lga and w.lga.state else None,
            'lga_id': w.lga_id,
            'ward_id': w.id,
        })

    # Search polling units
    pus = PollingUnit.query.join(Ward).join(LGA).join(State).filter(
        db.or_(PollingUnit.name.ilike(search_term), PollingUnit.code.ilike(search_term))
    ).limit(10).all()
    for p in pus:
        results.append({
            'type': 'polling_unit',
            'name': p.name,
            'code': p.code,
            'ward': p.ward.name if p.ward else None,
            'lga': p.ward.lga.name if p.ward and p.ward.lga else None,
            'state': p.ward.lga.state.name if p.ward and p.ward.lga and p.ward.lga.state else None,
            'state_code': p.ward.lga.state.code if p.ward and p.ward.lga and p.ward.lga.state else None,
        })

    return jsonify({'query': q, 'count': len(results), 'results': results})


# ── Autocomplete API ─────────────────────────────────────────────────────────

@app.route('/api/autocomplete')
def api_autocomplete():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])

    results = []
    search_term = f'%{q}%'

    # Elections
    elections = Election.query.filter(Election.name.ilike(search_term)).limit(3).all()
    for e in elections:
        results.append({
            'type': 'election', 'label': e.name, 'sub': e.status.title(),
            'url': url_for('election_overview', slug=e.slug),
            'icon': 'calendar-event'
        })

    # States
    states = State.query.filter(
        db.or_(State.name.ilike(search_term), State.code.ilike(search_term))
    ).limit(3).all()
    for s in states:
        results.append({
            'type': 'state', 'label': s.name, 'sub': s.geo_zone,
            'url': url_for('state_browse', state_code=s.code),
            'icon': 'geo-alt'
        })

    # LGAs
    lgas = LGA.query.join(State).filter(LGA.name.ilike(search_term)).limit(3).all()
    for l in lgas:
        results.append({
            'type': 'lga', 'label': l.name, 'sub': l.state.name if l.state else '',
            'url': url_for('lga_browse', state_code=l.state.code, lga_id=l.id) if l.state else '#',
            'icon': 'building'
        })

    # Wards
    wards = Ward.query.join(LGA).join(State).filter(
        Ward.name.ilike(search_term)
    ).limit(2).all()
    for w in wards:
        results.append({
            'type': 'ward', 'label': w.name,
            'sub': f'{w.lga.name}, {w.lga.state.name}' if w.lga and w.lga.state else '',
            'url': '#', 'icon': 'pin-map'
        })

    # Polling Units
    pus = PollingUnit.query.join(Ward).join(LGA).join(State).filter(
        db.or_(PollingUnit.name.ilike(search_term), PollingUnit.code.ilike(search_term))
    ).limit(2).all()
    for p in pus:
        results.append({
            'type': 'polling_unit', 'label': p.name,
            'sub': f'{p.ward.lga.name}, {p.ward.lga.state.name}' if p.ward and p.ward.lga and p.ward.lga.state else '',
            'url': '#', 'icon': 'box-seam'
        })

    return jsonify(results[:8])


# ── Search Page ──────────────────────────────────────────────────────────────

@app.route('/search')
def search_page():
    q = request.args.get('q', '').strip()
    results = {'elections': [], 'states': [], 'lgas': [], 'wards': [], 'polling_units': [], 'candidates': []}

    if q and len(q) >= 2:
        search_term = f'%{q}%'

        # Elections
        results['elections'] = Election.query.filter(
            db.or_(Election.name.ilike(search_term), Election.slug.ilike(search_term))
        ).limit(10).all()

        # States
        results['states'] = State.query.filter(
            db.or_(State.name.ilike(search_term), State.code.ilike(search_term))
        ).limit(10).all()

        # LGAs
        results['lgas'] = LGA.query.join(State).filter(
            LGA.name.ilike(search_term)
        ).limit(15).all()

        # Wards
        results['wards'] = Ward.query.join(LGA).join(State).filter(
            Ward.name.ilike(search_term)
        ).limit(15).all()

        # Polling Units
        results['polling_units'] = PollingUnit.query.join(Ward).join(LGA).join(State).filter(
            db.or_(PollingUnit.name.ilike(search_term), PollingUnit.code.ilike(search_term))
        ).limit(15).all()

        # Candidates
        results['candidates'] = Candidate.query.join(Party).join(ElectionType).join(Election).filter(
            db.or_(Candidate.name.ilike(search_term), Party.abbreviation.ilike(search_term))
        ).limit(15).all()

    total = sum(len(v) for v in results.values())
    return render_template('search.html', query=q, results=results, total=total)


# ── CSV Export ───────────────────────────────────────────────────────────────

@app.route('/export/csv/<slug>/<state_code>')
def export_csv_state(slug, state_code):
    election = Election.query.filter_by(slug=slug).first_or_404()
    state = State.query.filter_by(code=state_code).first_or_404()

    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()

    if not selected_type:
        return "No election type found", 404

    # Get LGA-level results
    lgas = LGA.query.filter_by(state_id=state.id).order_by(LGA.name).all()
    parties = []
    rows = []

    for lga in lgas:
        summary = get_results_summary(selected_type.id, 'lga', lga.id)
        row = {'LGA': lga.name}
        for p in summary:
            if p['abbreviation'] not in parties:
                parties.append(p['abbreviation'])
            row[p['abbreviation']] = p['total_votes']
        row['Total'] = sum(p['total_votes'] for p in summary)
        rows.append(row)

    output = io.StringIO()
    fieldnames = ['LGA'] + parties + ['Total']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, 0) for k in fieldnames})

    filename = f'{election.slug}_{state.code}_results.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@app.route('/export/csv/<slug>/<state_code>/<int:lga_id>')
def export_csv_lga(slug, state_code, lga_id):
    election = Election.query.filter_by(slug=slug).first_or_404()
    state = State.query.filter_by(code=state_code).first_or_404()
    lga = LGA.query.get_or_404(lga_id)

    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()

    if not selected_type:
        return "No election type found", 404

    wards = Ward.query.filter_by(lga_id=lga.id).order_by(Ward.name).all()
    parties = []
    rows = []

    for ward in wards:
        summary = get_results_summary(selected_type.id, 'ward', ward.id)
        row = {'Ward': ward.name}
        for p in summary:
            if p['abbreviation'] not in parties:
                parties.append(p['abbreviation'])
            row[p['abbreviation']] = p['total_votes']
        row['Total'] = sum(p['total_votes'] for p in summary)
        rows.append(row)

    output = io.StringIO()
    fieldnames = ['Ward'] + parties + ['Total']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, 0) for k in fieldnames})

    filename = f'{election.slug}_{state.code}_{lga.name}_results.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# ── Auto-refresh API (for live elections) ────────────────────────────────────

@app.route('/api/election/<slug>/live')
def api_election_live(slug):
    """Returns live data for auto-refresh on ongoing elections."""
    election = Election.query.filter_by(slug=slug).first_or_404()

    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()

    if not selected_type:
        return jsonify({'status': election.status, 'summary': [], 'states': []})

    # National summary
    national_summary = get_results_summary(selected_type.id, 'national', None)
    total_votes = sum(s['total_votes'] for s in national_summary)

    # Count total PUs reporting
    total_pus_reporting = Result.query.filter(
        Result.election_type_id == selected_type.id,
        Result.polling_unit_id.isnot(None),
    ).with_entities(Result.polling_unit_id).distinct().count()

    total_pus = PollingUnit.query.count()

    # Latest result timestamp
    latest = db.session.query(db.func.max(Result.updated_at)).filter(
        Result.election_type_id == selected_type.id
    ).scalar()

    return jsonify({
        'status': election.status,
        'total_votes': total_votes,
        'pus_reporting': total_pus_reporting,
        'total_pus': total_pus,
        'last_updated': latest.isoformat() if latest else None,
        'summary': [
            {
                'party': s['abbreviation'],
                'color': s['color'],
                'votes': s['total_votes'],
                'pct': round(s['total_votes'] / total_votes * 100, 1) if total_votes > 0 else 0,
            }
            for s in national_summary
        ],
    })


# ── Find My Polling Unit API ─────────────────────────────────────────────────

@app.route('/api/find-pu')
def api_find_pu():
    """Cascading data for Find My Polling Unit feature."""
    ward_id = request.args.get('ward_id', type=int)
    if ward_id:
        pus = PollingUnit.query.filter_by(ward_id=ward_id).order_by(PollingUnit.name).all()
        return jsonify([{
            'id': p.id, 'name': p.name, 'code': p.code,
            'registered_voters': p.registered_voters
        } for p in pus])
    return jsonify([])


# ── Admin: Save & Next helpers ───────────────────────────────────────────────

@app.route('/api/admin/next-pu')
@login_required
def api_admin_next_pu():
    """Get next polling unit in ward after given PU id."""
    ward_id = request.args.get('ward_id', type=int)
    current_pu_id = request.args.get('current_pu_id', type=int)
    if not ward_id:
        return jsonify({'next_pu': None})

    pus = PollingUnit.query.filter_by(ward_id=ward_id).order_by(PollingUnit.name).all()
    found = False
    for pu in pus:
        if found:
            return jsonify({'next_pu': {'id': pu.id, 'name': pu.name, 'code': pu.code}})
        if pu.id == current_pu_id:
            found = True

    return jsonify({'next_pu': None})


@app.route('/api/admin/existing-results')
@login_required
def api_admin_existing_results():
    """Check for existing results at a polling unit."""
    election_type_id = request.args.get('election_type_id', type=int)
    polling_unit_id = request.args.get('polling_unit_id', type=int)
    if not election_type_id or not polling_unit_id:
        return jsonify({'exists': False})

    results = Result.query.filter_by(
        election_type_id=election_type_id,
        polling_unit_id=polling_unit_id,
    ).all()

    if results:
        return jsonify({
            'exists': True,
            'results': [{
                'party': r.candidate.party.abbreviation if r.candidate and r.candidate.party else '?',
                'votes': r.votes,
                'entered_at': r.entered_at.strftime('%I:%M %p') if r.entered_at else None,
            } for r in results]
        })
    return jsonify({'exists': False})


# ── Share Card PNG Routes ─────────────────────────────────────────────────────

@app.route('/share/card/<slug>')
def share_card_election(slug):
    """Generate a PNG share card for election-level (national) results."""
    from share_card import generate_result_card

    election = Election.query.filter_by(slug=slug).first_or_404()
    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()
    if not selected_type:
        abort(404)

    summary = get_results_summary(selected_type.id, 'national', None)
    total_pus_rpt = Result.query.filter(
        Result.election_type_id == selected_type.id,
        Result.polling_unit_id.isnot(None),
    ).with_entities(Result.polling_unit_id).distinct().count()
    total_pus = PollingUnit.query.count()
    pct = round(total_pus_rpt / total_pus * 100, 1) if total_pus > 0 else 0

    buf = generate_result_card(election.name, 'National', summary, pct, election.status)
    resp = Response(buf.getvalue(), mimetype='image/png')
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp


@app.route('/share/card/<slug>/<state_code>')
def share_card_state(slug, state_code):
    """Generate a PNG share card for state-level results."""
    from share_card import generate_result_card

    election = Election.query.filter_by(slug=slug).first_or_404()
    state = State.query.filter_by(code=state_code.upper()).first_or_404()
    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()
    if not selected_type:
        abort(404)

    summary = get_results_summary(selected_type.id, 'state', state.id)
    pus_in_state = PollingUnit.query.join(Ward).join(LGA).filter(LGA.state_id == state.id).count()
    pus_rpt = Result.query.filter(
        Result.election_type_id == selected_type.id,
        Result.state_id == state.id,
        Result.polling_unit_id.isnot(None),
    ).with_entities(Result.polling_unit_id).distinct().count()
    pct = round(pus_rpt / pus_in_state * 100, 1) if pus_in_state > 0 else 0

    buf = generate_result_card(election.name, state.name, summary, pct, election.status)
    resp = Response(buf.getvalue(), mimetype='image/png')
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp


@app.route('/share/card/<slug>/<state_code>/<int:lga_id>')
def share_card_lga(slug, state_code, lga_id):
    """Generate a PNG share card for LGA-level results."""
    from share_card import generate_result_card

    election = Election.query.filter_by(slug=slug).first_or_404()
    lga = LGA.query.get_or_404(lga_id)
    type_slug = request.args.get('type', '')
    selected_type = None
    if type_slug:
        selected_type = ElectionType.query.filter_by(
            election_id=election.id, slug=type_slug
        ).first()
    if not selected_type:
        selected_type = ElectionType.query.filter_by(election_id=election.id).first()
    if not selected_type:
        abort(404)

    summary = get_results_summary(selected_type.id, 'lga', lga.id)
    pus_in_lga = PollingUnit.query.join(Ward).filter(Ward.lga_id == lga.id).count()
    pus_rpt = Result.query.filter(
        Result.election_type_id == selected_type.id,
        Result.lga_id == lga.id,
        Result.polling_unit_id.isnot(None),
    ).with_entities(Result.polling_unit_id).distinct().count()
    pct = round(pus_rpt / pus_in_lga * 100, 1) if pus_in_lga > 0 else 0

    buf = generate_result_card(election.name, lga.name, summary, pct, election.status)
    resp = Response(buf.getvalue(), mimetype='image/png')
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=5000)
