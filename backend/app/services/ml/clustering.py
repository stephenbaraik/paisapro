"""
KMeans stock clustering.

Groups stocks into 4 clusters (DEFENSIVE, VALUE, MOMENTUM, HIGH_VOLATILITY)
based on volatility, 30-day momentum, and beta vs Nifty.
Extracted from analytics.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from ...schemas.analytics import ClusteringResult, StockCluster, ClusterLabel
from ..universe import NIFTY_INDEX


def cluster_stocks(symbols: list[str]) -> ClusteringResult:
    from ..market_data import get_price_df

    nifty_df = get_price_df(NIFTY_INDEX, "1y")
    feat_rows: list[list[float]] = []
    valid: list[str] = []

    for sym in symbols:
        df = get_price_df(sym, "1y")
        if df is None or len(df) < 30:
            continue

        rets = df["daily_return"].dropna()
        ann_vol = float(rets.std() * np.sqrt(252))
        mom30 = float((df["close"].iloc[-1] / df["close"].iloc[-30]) - 1)

        beta = 1.0
        if nifty_df is not None and not nifty_df.empty:
            s_s = df.set_index("date")["daily_return"].dropna()
            n_s = nifty_df.set_index("date")["daily_return"].dropna()
            common = s_s.index.intersection(n_s.index)
            if len(common) > 30:
                c = np.cov(s_s[common].values, n_s[common].values)
                if c[1, 1] > 0:
                    beta = float(c[0, 1] / c[1, 1])

        feat_rows.append([ann_vol, mom30, beta])
        valid.append(sym)

    if len(valid) < 4:
        return ClusteringResult(clusters=[])

    X = np.array(feat_rows)
    X_sc = StandardScaler().fit_transform(X)
    km = KMeans(n_clusters=4, random_state=42, n_init=3)
    labels = km.fit_predict(X_sc)

    # Label clusters by centroid volatility (ascending → DEFENSIVE first)
    vol_order = np.argsort(km.cluster_centers_[:, 0])
    label_map = {
        vol_order[0]: ClusterLabel.DEFENSIVE,
        vol_order[1]: ClusterLabel.VALUE,
        vol_order[2]: ClusterLabel.MOMENTUM,
        vol_order[3]: ClusterLabel.HIGH_VOLATILITY,
    }

    clusters = [
        StockCluster(
            symbol=valid[i],
            cluster_id=int(labels[i]),
            cluster_label=label_map[int(labels[i])],
            volatility=round(feat_rows[i][0] * 100, 2),
            momentum_30d=round(feat_rows[i][1] * 100, 2),
            beta=round(feat_rows[i][2], 3),
        )
        for i in range(len(valid))
    ]
    return ClusteringResult(clusters=clusters)
