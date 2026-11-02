"""Reproduce the 2024–25 NHL shot-volume vs. quality analysis offline."""
from pathlib import Path
import json
import hashlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent

def calculate_metrics(raw):
    """Validate the fixed 32-team cohort and return metrics without file writes."""
    cols = ['team', 'season', 'situation', 'iceTime',
            'unblockedShotAttemptsFor', 'xGoalsFor']
    if not set(cols).issubset(raw.columns):
        raise ValueError('Required columns missing')
    df = raw.loc[raw.situation.eq('5on5'), cols].copy()
    if len(df) != 32 or not df.team.is_unique or df.isna().any().any():
        raise ValueError('Expected 32 unique, complete team records')
    numeric = ['season', 'iceTime', 'unblockedShotAttemptsFor', 'xGoalsFor']
    if any(not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]) for c in numeric):
        raise ValueError('Metrics must be finite numeric values')
    if not np.isfinite(df[numeric].to_numpy()).all():
        raise ValueError('Metrics must be finite numeric values')
    if not df.season.eq(2024).all():
        raise ValueError('Expected season 2024')
    if not df.iceTime.gt(0).all() or not df.unblockedShotAttemptsFor.gt(0).all():
        raise ValueError('Time and attempt denominators must be positive')
    if not df.xGoalsFor.between(0, df.unblockedShotAttemptsFor).all():
        raise ValueError('Expected goals must be between zero and attempts')
    df['attempts_per_60'] = df.unblockedShotAttemptsFor / df.iceTime * 3600
    df['xg_per_attempt'] = df.xGoalsFor / df.unblockedShotAttemptsFor
    df['xg_per_60'] = df.xGoalsFor / df.iceTime * 3600
    assert np.allclose(df.attempts_per_60 * df.xg_per_attempt, df.xg_per_60)
    return df


def main():
    source = ROOT / 'data/teams_2024.csv'
    df = calculate_metrics(pd.read_csv(source))
    x, y = df.attempts_per_60, df.xg_per_attempt
    loo = [x.drop(i).corr(y.drop(i)) for i in df.index]
    summary = {
        'season': '2024-25', 'scope': 'regular season, 5-on-5',
        'teams': len(df), 'pearson_r': x.corr(y),
        'spearman_r': x.rank().corr(y.rank()),
        'leave_one_team_out_min': min(loo),
        'leave_one_team_out_max': max(loo),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    df.sort_values('attempts_per_60', ascending=False).to_csv(out / 'team_metrics.csv', index=False)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 8))
    points = ax.scatter(x, y * 100, c=df.xg_per_60, cmap='viridis', s=110,
                        edgecolors='white', linewidths=0.8)
    for row in df.itertuples():
        ax.annotate(row.team, (row.attempts_per_60, row.xg_per_attempt * 100),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    ax.axvline(x.mean(), color='gray', linestyle='--', linewidth=1)
    ax.axhline(y.mean() * 100, color='gray', linestyle='--', linewidth=1)
    ax.set(xlabel='Unblocked shot attempts per 60 minutes',
           ylabel='Expected scoring probability per attempt (%)',
           title=f'NHL shot volume vs. quality | 2024–25, 5-on-5\n32 teams · Pearson r = {summary["pearson_r"]:.3f}')
    fig.colorbar(points, ax=ax, label='Expected goals per 60 minutes')
    fig.text(.08, .02, 'Source: MoneyPuck.com | Dashed lines: unweighted team means', fontsize=9)
    fig.tight_layout(rect=[0, .04, 1, 1])
    fig.savefig(out / 'volume_vs_quality.png', dpi=180)
    plt.close(fig)
    print(json.dumps(summary, indent=2))
    return df, summary

if __name__ == '__main__':
    main()

