import os
import json
from flask import Flask, render_template, jsonify
from data import (
    FCT_RESULTS, FCT_CHAIRMANSHIP_WINNERS,
    RIVERS_BYELECTIONS, KANO_BYELECTIONS,
    ELECTION_INFO, PARTY_COLORS,
)

app = Flask(__name__)


@app.route("/")
def index():
    # FCT stats
    fct_total_units = 0
    fct_total_votes = 0
    fct_party_totals = {}

    for ac, wards in FCT_RESULTS.items():
        for ward, units in wards.items():
            for unit, parties in units.items():
                fct_total_units += 1
                for party, votes in parties.items():
                    fct_total_votes += votes
                    fct_party_totals[party] = fct_party_totals.get(party, 0) + votes

    fct_sorted_parties = sorted(fct_party_totals.items(), key=lambda x: x[1], reverse=True)

    return render_template(
        "index.html",
        fct_results=FCT_RESULTS,
        chairmanship_winners=FCT_CHAIRMANSHIP_WINNERS,
        rivers=RIVERS_BYELECTIONS,
        kano=KANO_BYELECTIONS,
        info=ELECTION_INFO,
        party_colors=PARTY_COLORS,
        fct_total_units=fct_total_units,
        fct_total_votes=fct_total_votes,
        fct_sorted_parties=fct_sorted_parties,
    )


@app.route("/api/results")
def api_results():
    return jsonify({
        "fct": FCT_RESULTS,
        "chairmanship_winners": FCT_CHAIRMANSHIP_WINNERS,
        "rivers": RIVERS_BYELECTIONS,
        "kano": KANO_BYELECTIONS,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
