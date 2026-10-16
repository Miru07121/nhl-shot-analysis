"""Compare observed 5-on-5 goals with MoneyPuck expected goals."""
from pathlib import Path
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent

def main():
    df = pd.read_csv(ROOT.parents[1] / 'data/teams_2024.csv')
    df = df.loc[df.situation.eq('5on5'), ['team','season','iceTime','goalsFor','xGoalsFor','unblockedShotAttemptsFor']].copy()
    assert len(df) == 32 and df.team.is_unique and df.season.eq(2024).all()
    assert not df.isna().any().any() and df.iceTime.gt(0).all()
    assert df.goalsFor.ge(0).all() and df.xGoalsFor.gt(0).all()
    df['goals_per_60'] = df.goalsFor / df.iceTime * 3600
    df['xg_per_60'] = df.xGoalsFor / df.iceTime * 3600
    df['goals_above_expected'] = df.goalsFor - df.xGoalsFor
    df['gap_per_60'] = df.goals_per_60 - df.xg_per_60
    df['goals_to_xg_ratio'] = df.goalsFor / df.xGoalsFor
    assert np.allclose(df.gap_per_60, df.goals_above_expected / df.iceTime * 3600)
    df = df.sort_values('gap_per_60', ascending=False)
    summary = {'teams':len(df),'pearson_xg60_goals60':df.xg_per_60.corr(df.goals_per_60),
        'league_goals':float(df.goalsFor.sum()),'league_xg':float(df.xGoalsFor.sum()),
        'largest_positive_gap':df.iloc[0][['team','gap_per_60','goals_above_expected']].to_dict(),
        'largest_negative_gap':df.iloc[-1][['team','gap_per_60','goals_above_expected']].to_dict()}
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    df.to_csv(out/'team_finishing.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(13,8),gridspec_kw={'width_ratios':[1.1,1]})
    axes[0].scatter(df.xg_per_60,df.goals_per_60,c='#137c8b',s=60)
    for r in df.itertuples():
        axes[0].annotate(r.team,(r.xg_per_60,r.goals_per_60),xytext=(3,4),textcoords='offset points',fontsize=7)
    lo=min(df.xg_per_60.min(),df.goals_per_60.min())-.1
    hi=max(df.xg_per_60.max(),df.goals_per_60.max())+.1
    axes[0].plot([lo,hi],[lo,hi],color='gray',ls='--',label='Goals = xG')
    axes[0].set(xlabel='Expected goals per 60',ylabel='Observed goals per 60',title='Chance creation and actual scoring')
    axes[0].legend()
    ordered=df.sort_values('gap_per_60')
    axes[1].barh(ordered.team,ordered.gap_per_60,color=['#c25d45' if v<0 else '#137c8b' for v in ordered.gap_per_60])
    axes[1].axvline(0,color='black',lw=.7)
    axes[1].set(xlabel='Goals minus xG per 60',title='Finishing residual by team')
    fig.suptitle('NHL finishing versus expected goals | 2024–25 regular season, 5-on-5',fontsize=14)
    fig.text(.02,.01,'Data: MoneyPuck.com | Residuals combine skill, randomness, opponent goaltending and model error.',fontsize=9)
    fig.tight_layout(rect=[0,.035,1,.95]);fig.savefig(out/'finishing.png',dpi=160);plt.close(fig)
    print(json.dumps(summary,indent=2))
    return df,summary

if __name__=='__main__': main()
