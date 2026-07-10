"""
predict_router.py
-----------------
GET /predict/random
  → Picks a random sample from x_test_scaled.csv
  → Returns:
      • the 140 scaled feature values
      • Isolation Forest prediction  (0 = normal, 1 = anomaly)
      • Autoencoder reconstruction MSE  (rounded)
      • Autoencoder prediction       (0 = normal, 1 = anomaly)
      • The real label from y_test.csv (0 = normal, 1 = fraud)
"""

import os
import warnings
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

# ── Paths (resolve relative to this file's location) ──────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent   # …/depi/

X_TEST_PATH = BASE_DIR / "x_test_scaled.csv"
Y_TEST_PATH = BASE_DIR / "y_test.csv"
ISO_PATH    = BASE_DIR / "iso_model.joblib"
AE_PATH     = BASE_DIR / "my_autoencoder.keras"

# ── Autoencoder anomaly threshold (MSE) ───────────────────────────────────────
# Adjust this to match the threshold you chose during training.
AE_THRESHOLD = 1  # MSE ≥ 1  →  anomaly

router = APIRouter(prefix="/predict", tags=["Prediction"])


# ── Module-level state (lazy-loaded once on first request) ─────────────────────
_iso_model        = None
_autoencoder      = None
_ae_load_error    = None   # str if autoencoder failed to load, None if ok
_x_test           = None
_y_test           = None


def _try_load_autoencoder():
    """
    Try to load my_autoencoder.keras safely without crashing the app.
    """
    if not AE_PATH.exists():
        return None, f"my_autoencoder.keras not found at {AE_PATH}"

    # --- attempt 1: standalone keras (keras>=3) --------------------------------
    try:
        import keras as _keras
        model = _keras.models.load_model(str(AE_PATH))
        return model, None
    except ImportError:
        pass                            # keras not installed
    except Exception as exc:
        pass                            # keras installed but load failed

    # --- attempt 2: tensorflow.keras -------------------------------------------
    try:
        from tensorflow import keras as _keras  # type: ignore
        model = _keras.models.load_model(str(AE_PATH))
        return model, None
    except ImportError:
        pass

    return (
        None,
        (
            "Autoencoder unavailable: neither 'keras' nor 'tensorflow' is installed "
            "in this environment. Run:  "
            ".\\venv\\Scripts\\pip install keras \"jax[cpu]\"  "
            "(TensorFlow requires Python ≤ 3.12)"
        ),
    )


def _load_resources():
    global _iso_model, _autoencoder, _ae_load_error, _x_test, _y_test

    # ── Isolation Forest (required) ───────────────────────────────────────────
    if _iso_model is None:
        if not ISO_PATH.exists():
            raise FileNotFoundError(f"iso_model.joblib not found at {ISO_PATH}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _iso_model = joblib.load(ISO_PATH)

    # ── Autoencoder (optional) ────────────────────────────────────────────────
    if _autoencoder is None and _ae_load_error is None:
        _autoencoder, _ae_load_error = _try_load_autoencoder()

    # ── Test data ─────────────────────────────────────────────────────────────
    if _x_test is None:
        if not X_TEST_PATH.exists():
            raise FileNotFoundError(f"x_test_scaled.csv not found at {X_TEST_PATH}")
        _x_test = pd.read_csv(X_TEST_PATH).values   # (N, 140)

    if _y_test is None:
        if not Y_TEST_PATH.exists():
            raise FileNotFoundError(f"y_test.csv not found at {Y_TEST_PATH}")
        _y_test = pd.read_csv(Y_TEST_PATH)["Label"].values  # (N,)


# ── Route ──────────────────────────────────────────────────────────────────────
@router.get(
    "/random",
    summary="Predict on a random test sample",
    description="Returns predictions strictly as 0 (normal) or 1 (anomaly/fraud)."
)
def predict_random():
    try:
        _load_resources()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # ── Pick a random index ────────────────────────────────────────────────────
    n_samples = _x_test.shape[0]
    idx = int(np.random.randint(0, n_samples))

    # ── Feature row ───────────────────────────────────────────────────────────
    sample_2d = _x_test[idx].reshape(1, -1)  # (1, 140)

    # ── Isolation Forest ──────────────────────────────────────────────────────
    raw_iso_pred = int(_iso_model.predict(sample_2d)[0])
    # Convert scikit-learn format (1 = normal, -1 = anomaly) to (0 = normal, 1 = anomaly)
    final_iso_pred = 0 if raw_iso_pred == 1 else 1

    # ── Autoencoder (optional) ────────────────────────────────────────────────
    if _autoencoder is not None:
        reconstruction = _autoencoder.predict(sample_2d, verbose=0)
        mse = float(np.mean(np.power(sample_2d.flatten() - reconstruction.flatten(), 2)))
        mse_rounded = round(mse, 6)
        
        # Threshold calculation: (anomaly) -> 1, (normal) -> 0
        final_ae_pred = 1 if mse_rounded >= AE_THRESHOLD else 0

        autoencoder_result = {
            "available": True,
            "reconstruction_mse": mse_rounded,
            "prediction": final_ae_pred
        }
    else:
        autoencoder_result = {
            "available": False,
            "error": _ae_load_error,
        }

    # ── Real label ────────────────────────────────────────────────────────────
    real_label = int(_y_test[idx])

    return {
        "sample_index": idx,
        "features": _x_test[idx].tolist(),
        "isolation_forest": {
            "prediction": final_iso_pred
        },
        "autoencoder": autoencoder_result,
        "real_label": {
            "value": real_label
        }
    }