import os
import json
from flask import Flask, render_template, jsonify, request
from data import RESULTS, ELECTION_INFO, PARTY_COLORS

app = Flask(__name__)


@app.route("/")
def index():
    # Compute summary stats
    total_units = 0
    total_votes = 0
    party_totals = {}

    for ac, wards in RESULTS.items():
        for ward, units in wards.items():
            for unit, parties in units.items():
                total_units += 1
                for party, votes in parties.items():
                    total_votes += votes
                    party_totals[party] = party_totals.get(party, 0) + votes

    # Sort parties by total votes
    sorted_parties = sorted(party_totals.items(), key=lambda x: x[1], reverse=True)

    return render_template(
        "index.html",
        results=RESULTS,
        results_json=json.dumps(RESULTS),
        info=ELECTION_INFO,
        party_colors=PARTY_COLORS,
        party_colors_json=json.dumps(PARTY_COLORS),
        total_units=total_units,
        total_votes=total_votes,
        sorted_parties=sorted_parties,
    )


@app.route("/api/results")
def api_results():
    return jsonify(RESULTS)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
