"""Continuous Operating Condition Normalizer.

Replaces discrete K-Means regime clustering with a polynomial Ridge regression
that models the expected nominal sensor value as a smooth function of operating
conditions (op1, op2, op3).  This eliminates discrete boundary-jumping artifacts
that severely degrade accuracy on multi-regime subsets (FD002, FD004).
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from .data import OPS, SENS


class ContinuousRegimeNormalizer:
    """Model expected nominal sensor readings as a smooth polynomial surface
    over operating conditions, then return deviations from that surface.

    Fit on *training* data only; apply to train/test/stream identically.

    Parameters
    ----------
    degree : int
        Polynomial degree for the operating-condition features.
    alpha : float
        Ridge regularisation strength.
    sensors : list[str] or None
        Subset of sensor columns to model.  ``None`` uses all 21.
    """

    def __init__(self, degree: int = 3, alpha: float = 1.0, sensors=None):
        self.degree = degree
        self.alpha = alpha
        self.sensors = sensors if sensors is not None else list(SENS)
        self._pipe = None

    # ------------------------------------------------------------------ fit
    def fit(self, ops_train, sensors_train):
        """Fit polynomial Ridge regression: sensors ~ f(ops).

        Parameters
        ----------
        ops_train : array-like, shape (n, 3)
            Operating-condition columns (op1, op2, op3) from the training set.
        sensors_train : array-like, shape (n, S)
            Sensor readings corresponding to ``ops_train``.

        Returns
        -------
        self
        """
        X = np.asarray(ops_train, dtype=np.float64)
        Y = np.asarray(sensors_train, dtype=np.float64)
        if Y.ndim == 1:
            Y = Y[:, None]

        # StandardScaler → PolynomialFeatures → Ridge  (multi-output)
        self._pipe = make_pipeline(
            StandardScaler(),
            PolynomialFeatures(degree=self.degree, include_bias=True),
            Ridge(alpha=self.alpha),
        )
        self._pipe.fit(X, Y)
        return self

    # -------------------------------------------------------------- predict
    def _predict_nominal(self, ops):
        """Return predicted nominal sensor values for given operating conditions."""
        X = np.asarray(ops, dtype=np.float64)
        return self._pipe.predict(X)

    # ----------------------------------------------------------- transform
    def transform_deviations(self, ops, sensors):
        """Compute deviations = raw_sensors − predicted_nominal.

        Parameters
        ----------
        ops : array-like, shape (n, 3)
        sensors : array-like, shape (n, S)

        Returns
        -------
        deviations : np.ndarray, shape (n, S)
        """
        Y = np.asarray(sensors, dtype=np.float64)
        if Y.ndim == 1:
            Y = Y[:, None]
        nominal = self._predict_nominal(ops)
        return Y - nominal

    # ------------------------------------------------------ convenience
    def fit_transform(self, ops, sensors):
        """Fit on the data and return deviations in one call."""
        self.fit(ops, sensors)
        return self.transform_deviations(ops, sensors)
