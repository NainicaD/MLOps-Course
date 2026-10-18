# Docker Lab 2 (Modified): Wine Cultivar Classifier with a Multi-Stage Build

This lab trains a machine learning model and serves it as a web app, all inside Docker, using a **multi-stage build**.

## What the app does

The model predicts which of three grape cultivars (A, B or C) a wine came from, using four lab measurements: alcohol, flavanoids, color intensity and proline. It uses the UCI Wine dataset (178 samples), which ships with scikit-learn, so nothing is downloaded during training. The model is a Random Forest classifier.

## Key terms

- **Image:** A packaged snapshot of an app and everything it needs to run.
- **Container:** A running copy of an image.
- **Multi-stage build:** A Dockerfile with more than one `FROM` line. Each stage starts fresh, and later stages copy only what they need from earlier ones.

## How the build works

| Stage | What it does |
|---|---|
| 1. `model_training` | Installs the packages, runs `model_training.py`, and saves `wine_model.joblib` |
| 2. `serving` | Starts from a clean image, copies in only the saved model plus the Flask app, and runs the server on port 4000 |

The training script never makes it into the final image, so the image that runs the app stays clean.

## Folder structure

```
Lab2_WineClassifier/
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── README.md
└── src/
    ├── model_training.py   # Stage 1: trains and saves the model
    ├── main.py             # Stage 2: Flask app
    ├── templates/
    │   └── predict.html    # Web form
    └── statics/
        └── styles.css
```

## How to run

1. Open Docker Desktop and wait until it says it's running.
2. In a terminal, go to this folder:
   ```
   cd Labs/Docker_Labs/Lab2_WineClassifier
   ```
3. Build the image:
   ```
   docker build -t wine-flask-app .
   ```
   The build log prints the model's test accuracy and a classification report from Stage 1.
4. Run the container:
   ```
   docker run -p 80:4000 wine-flask-app
   ```
5. Open http://localhost/predict in your browser, enter the four values and click **Predict**.

To stop the app, press `Ctrl+C` in the terminal.

## Optional: call the API directly

```
curl -X POST http://localhost/predict \
  -H "Content-Type: application/json" \
  -d '{"alcohol": 13.2, "flavanoids": 2.8, "color_intensity": 5.6, "proline": 1050}'
```

Example response:

```
{"confidence": 1.0, "predicted_cultivar": "Cultivar A", "probabilities": {"Cultivar A": 1.0, "Cultivar B": 0.0, "Cultivar C": 0.0}}
```

## Example inputs

| Cultivar | Alcohol | Flavanoids | Color intensity | Proline |
|---|---|---|---|---|
| A | 13.2 | 2.8 | 5.6 | 1050 |
| B | 12.3 | 2.0 | 2.8 | 500 |
| C | 13.1 | 0.7 | 7.5 | 630 |
