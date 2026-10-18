# Docker Lab 2 (Modified): Breast Tumor Classifier with a Multi-Stage Build

This lab trains a machine learning model and serves it as a web app, all inside Docker, using a **multi-stage build**.

## What the app does

The model predicts whether a breast tumor is **malignant** or **benign** from four measurements of cell nuclei in a biopsy image: mean radius, mean texture, worst concave points and worst area. It uses the Wisconsin Breast Cancer dataset (569 samples), which ships with scikit-learn, so nothing is downloaded during training. The model is a logistic regression with feature scaling, and it reaches about 95% accuracy on held-out test data.

This is a course demo, not a diagnostic tool.

## Key terms

- **Image:** A packaged snapshot of an app and everything it needs to run.
- **Container:** A running copy of an image.
- **Multi-stage build:** A Dockerfile with more than one `FROM` line. Each stage starts fresh, and later stages copy only what they need from earlier ones.

## How the build works

| Stage | What it does |
|---|---|
| 1. `model_training` | Installs the packages, runs `model_training.py`, and saves `tumor_model.joblib` |
| 2. `serving` | Starts from a clean image, copies in only the saved model plus the Flask app, and runs the server on port 4000 |

The training script never makes it into the final image, so the image that runs the app stays clean.

## Folder structure

```
Lab2_TumorClassifier/
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
   cd Labs/Docker_Labs/Lab2_TumorClassifier
   ```
3. Build the image:
   ```
   docker build -t tumor-flask-app .
   ```
   The build log prints the model's test accuracy and a classification report from Stage 1.
4. Run the container:
   ```
   docker run -p 80:4000 tumor-flask-app
   ```
5. Open http://localhost/predict in your browser, enter the four values and click **Predict**.

To stop the app, press `Ctrl+C` in the terminal.

## Optional: call the API directly

```
curl -X POST http://localhost/predict \
  -H "Content-Type: application/json" \
  -d '{"radius_mean": 12.2, "texture_mean": 17.4, "concave_points_worst": 0.074, "area_worst": 547}'
```

Example response:

```
{"confidence": 0.993, "prediction": "Benign", "probabilities": {"Benign": 0.993, "Malignant": 0.007}}
```

## Example inputs

These are close to the median values for each class in the dataset.

| Expected result | Mean radius | Mean texture | Worst concave points | Worst area |
|---|---|---|---|---|
| Benign | 12.2 | 17.4 | 0.074 | 547 |
| Malignant | 17.3 | 21.5 | 0.18 | 1300 |
