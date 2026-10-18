"""Stage 1 of the Docker build: train a tumor classifier and save it."""
import joblib
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# Four cell-nucleus measurements from the Wisconsin Breast Cancer dataset
# (bundled with scikit-learn, so no download is needed)
COLUMNS = {
    "mean radius": "radius_mean",
    "mean texture": "texture_mean",
    "worst concave points": "concave_points_worst",
    "worst area": "area_worst",
}
FEATURES = list(COLUMNS.values())
CLASS_NAMES = ["Malignant", "Benign"]  # scikit-learn labels: 0 = malignant, 1 = benign
MODEL_PATH = "tumor_model.joblib"


def main():
    data = load_breast_cancer(as_frame=True)
    X = data.data[list(COLUMNS)].rename(columns=COLUMNS)
    y = data.target

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Scale the features, then fit a logistic regression
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    print(f"Test accuracy: {accuracy_score(y_test, preds):.3f}")
    print(classification_report(y_test, preds, target_names=CLASS_NAMES))

    # Save the model together with the feature order and class names the API needs
    joblib.dump(
        {"model": model, "features": FEATURES, "class_names": CLASS_NAMES},
        MODEL_PATH,
    )
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
