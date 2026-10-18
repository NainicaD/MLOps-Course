"""Stage 2 of the Docker build: serve the trained model with Flask."""
import joblib
import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__, static_folder="statics", template_folder="templates")

bundle = joblib.load("wine_model.joblib")
model = bundle["model"]
FEATURES = bundle["features"]
CLASS_NAMES = bundle["class_names"]


@app.route("/")
def home():
    return "Wine Cultivar Classifier is running. Go to /predict to use it."


@app.route("/predict", methods=["GET", "POST"])
def predict():
    if request.method == "GET":
        return render_template("predict.html", features=FEATURES)

    # Accept either an HTML form or a JSON body
    data = request.get_json(silent=True) or request.form
    try:
        row = {f: float(data[f]) for f in FEATURES}
    except (KeyError, ValueError):
        return jsonify({"error": f"Send numeric values for: {', '.join(FEATURES)}"}), 400

    X = pd.DataFrame([row], columns=FEATURES)
    probs = model.predict_proba(X)[0]
    best = int(probs.argmax())

    return jsonify({
        "predicted_cultivar": CLASS_NAMES[best],
        "confidence": round(float(probs[best]), 3),
        "probabilities": {name: round(float(p), 3) for name, p in zip(CLASS_NAMES, probs)},
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)
