"""Stage 1 of the Docker build: train a wine cultivar classifier and save it."""
import joblib
from sklearn.datasets import load_wine
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

# Four measurements from the UCI Wine dataset (bundled with scikit-learn, so no download is needed)
FEATURES = ["alcohol", "flavanoids", "color_intensity", "proline"]
CLASS_NAMES = ["Cultivar A", "Cultivar B", "Cultivar C"]
MODEL_PATH = "wine_model.joblib"


def main():
    wine = load_wine(as_frame=True)
    X = wine.data[FEATURES]
    y = wine.target

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42)
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
