import os
import base64
import pickle

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "model")

TARGET_COL = "progression"      # disease progression score one year after baseline
DEPTHS = list(range(1, 16))     # max_depth values to search (plays the role of k in the original)


def _encode(obj):
    """Pickle + base64 so the payload is JSON-safe for XCom."""
    return base64.b64encode(pickle.dumps(obj)).decode("ascii")


def _decode(payload):
    return pickle.loads(base64.b64decode(payload))


def _rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def load_data():
    """
    Step 1 - Load the diabetes dataset from data/file.csv.
    Returns the DataFrame serialized as a base64 string.
    """
    df = pd.read_csv(os.path.join(DATA_DIR, "file.csv"))
    print(f"Loaded {df.shape[0]} rows x {df.shape[1]} columns")
    return _encode(df)


def data_preprocessing(data):
    """
    Step 2 - Drop missing values, separate features from the target,
    and split into training and validation sets (80/20).
    """
    df = _decode(data).dropna()
    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"Train: {X_train.shape}  |  Validation: {X_val.shape}")
    return _encode(
        {"X_train": X_train, "X_val": X_val, "y_train": y_train, "y_val": y_val}
    )


def build_save_model(data, filename):
    """
    Step 3 - Train a Random Forest regressor for each max_depth in DEPTHS,
    record validation RMSE for each, and save the best model.
    Returns the list of validation RMSE scores.
    """
    d = _decode(data)

    val_rmse, models = [], []
    for depth in DEPTHS:
        rf = RandomForestRegressor(
            n_estimators=200, max_depth=depth, random_state=42, n_jobs=-1
        ).fit(d["X_train"], d["y_train"])
        val_rmse.append(_rmse(d["y_val"], rf.predict(d["X_val"])))
        models.append(rf)
        print(f"max_depth={depth:2d}  validation RMSE={val_rmse[-1]:.2f}")

    best_model = models[int(np.argmin(val_rmse))]

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, filename), "wb") as f:
        pickle.dump(
            {"model": best_model, "feature_names": list(d["X_train"].columns)}, f
        )
    return val_rmse


def load_model_evaluate(filename, val_rmse):
    """
    Step 4 - Load the saved model, report the best max_depth,
    and evaluate it on the held-out rows in data/test.csv.
    Returns the test-set metrics.
    """
    with open(os.path.join(MODEL_DIR, filename), "rb") as f:
        bundle = pickle.load(f)
    model = bundle["model"]

    best_depth = DEPTHS[int(np.argmin(val_rmse))]
    print(f"Best max_depth (lowest validation RMSE): {best_depth}")

    test_df = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))
    X_test = test_df[bundle["feature_names"]]
    y_test = test_df[TARGET_COL]
    preds = model.predict(X_test)

    metrics = {
        "best_max_depth": best_depth,
        "test_rmse": round(_rmse(y_test, preds), 2),
        "test_mae": round(float(mean_absolute_error(y_test, preds)), 2),
        "test_r2": round(float(r2_score(y_test, preds)), 3),
    }
    print(f"Test metrics: {metrics}")

    importances = sorted(
        zip(bundle["feature_names"], model.feature_importances_),
        key=lambda t: t[1], reverse=True,
    )
    print("Top features:", ", ".join(f"{n} ({v:.2f})" for n, v in importances[:3]))

    for actual, pred in list(zip(y_test, preds))[:5]:
        print(f"actual={actual:.0f}  predicted={pred:.0f}")

    return metrics
