from __future__ import annotations

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class TopCategoryReducer(BaseEstimator, TransformerMixin):
    """
    Reduce high-cardinality categorical columns by keeping only top_k categories
    and mapping the rest to '__OTHER__'.
    """

    def __init__(self, top_k: int = 30, other_label: str = "__OTHER__"):
        self.top_k = top_k
        self.other_label = other_label
        self.top_categories_ = None  # learned in fit()

    def fit(self, X: pd.DataFrame, y=None):
        # Learn top_k categories per column from the training data.
        X_df = pd.DataFrame(X).copy()
        self.top_categories_ = {}
        for col in X_df.columns:
            top = X_df[col].astype(str).value_counts(dropna=False).head(self.top_k).index.tolist()
            self.top_categories_[col] = set(top)
        return self

    def transform(self, X: pd.DataFrame):
        # Map infrequent categories to other_label.
        X_df = pd.DataFrame(X).copy()
        for col in X_df.columns:
            allowed = self.top_categories_.get(col, set())
            X_df[col] = X_df[col].astype(str).where(X_df[col].astype(str).isin(allowed), self.other_label)
        return X_df
