"""
Populate all LGAs with wards and polling units.
Generates realistic ward/PU counts per LGA based on Nigerian averages.
Skips LGAs that already have wards (e.g. FCT from legacy migration).
"""
import random
from models import db, State, LGA, Ward, PollingUnit

# Realistic PU location prefixes
PU_LOCATIONS = [
    "Primary School", "Secondary School", "Community Hall", "Town Hall",
    "Market Square", "Health Centre", "Village Square", "Mosque Area",
    "Church Premises", "Palace Grounds", "Open Space", "Civic Centre",
    "Playground", "Under Tree", "Motor Park", "Junction",
    "Custom Office", "Police Station Area", "Post Office",
    "Dispensary", "Community Centre",
]

random.seed(42)


def seed_wards_and_pus():
    """Generate wards and polling units for all LGAs."""
    states = State.query.order_by(State.name).all()
    total_wards = 0
    total_pus = 0

    for state in states:
        lgas = LGA.query.filter_by(state_id=state.id).order_by(LGA.name).all()
        state_wards = 0
        state_pus = 0

        for lga in lgas:
            # Skip if this LGA already has wards
            existing = Ward.query.filter_by(lga_id=lga.id).count()
            if existing > 0:
                state_wards += existing
                state_pus += PollingUnit.query.join(Ward).filter(Ward.lga_id == lga.id).count()
                continue

            # Generate 10-15 wards per LGA
            num_wards = random.randint(10, 15)
            for w_idx in range(1, num_wards + 1):
                ward = Ward(
                    name=f"{lga.name} Ward {w_idx:02d}",
                    lga_id=lga.id,
                )
                db.session.add(ward)
                db.session.flush()
                state_wards += 1

                # Generate 15-25 PUs per ward
                num_pus = random.randint(15, 25)
                for p_idx in range(1, num_pus + 1):
                    location = random.choice(PU_LOCATIONS)
                    pu = PollingUnit(
                        name=f"{location} {p_idx:03d}, {ward.name}",
                        code=f"{state.code}/{lga.id:03d}/{ward.id:05d}/{p_idx:03d}",
                        ward_id=ward.id,
                        registered_voters=random.randint(300, 2500),
                    )
                    db.session.add(pu)
                    state_pus += 1

            # Flush per LGA to keep memory manageable
            db.session.flush()

        total_wards += state_wards
        total_pus += state_pus
        print(f"  {state.name:20s} — {len(lgas):3d} LGAs, {state_wards:5d} wards, {state_pus:6d} PUs")

    db.session.commit()
    print("=" * 60)
    print(f"TOTAL: {total_wards:,} wards, {total_pus:,} polling units")
    print("=" * 60)


if __name__ == "__main__":
    from app import app
    with app.app_context():
        print("Seeding wards and polling units for all LGAs...")
        seed_wards_and_pus()
