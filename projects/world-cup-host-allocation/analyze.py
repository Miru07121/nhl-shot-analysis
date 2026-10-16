"""Descriptive allocation analysis of the 2026 World Cup schedule."""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent

def main():
    df=pd.read_csv(ROOT/'data/venues.csv')
    stages=['group','round32','round16','quarterfinal','semifinal','third_place','final']
    assert len(df)==16 and df.city.is_unique and not df.isna().any().any()
    assert (df[stages]>=0).all().all()
    assert (df[stages]%1==0).all().all()
    assert df[stages].sum().tolist()==[72,16,8,4,2,1,1]
    df['total_matches']=df[stages].sum(axis=1)
    df['knockout_matches']=df.total_matches-df.group
    df['match_share_pct']=df.total_matches/104*100
    country=df.groupby('country').agg(venues=('city','size'),group_matches=('group','sum'),knockout_matches=('knockout_matches','sum'),total_matches=('total_matches','sum'))
    assert country.total_matches.to_dict()=={'Canada':13,'Mexico':13,'United States':78}
    country['venue_share_pct']=country.venues/16*100
    country['match_share_pct']=country.total_matches/104*100
    country['knockout_share_pct']=country.knockout_matches/32*100
    country['matches_per_venue']=country.total_matches/country.venues
    country['allocation_index']=country.match_share_pct/country.venue_share_pct
    van=df.loc[df.city.eq('Vancouver')].iloc[0]
    summary={'matches':int(df.total_matches.sum()),'venues':len(df),
        'us_match_share_pct':float(country.loc['United States','match_share_pct']),
        'us_knockout_share_pct':float(country.loc['United States','knockout_share_pct']),
        'vancouver_matches':int(van.total_matches),
        'vancouver_share_of_canadian_matches_pct':float(van.total_matches/13*100),
        'vancouver_match_count_rank':int(df.total_matches.rank(method='min',ascending=False)[df.city.eq('Vancouver')].iloc[0]),
        'largest_allocation_city':df.loc[df.total_matches.idxmax(),'city']}
    out=ROOT/'results';out.mkdir(exist_ok=True)
    df.to_csv(out/'venue_metrics.csv',index=False);country.to_csv(out/'country_metrics.csv')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(13,7))
    ordered=df.sort_values(['total_matches','city'])
    axes[0].barh(ordered.city,ordered.group,label='Group',color='#137c8b')
    axes[0].barh(ordered.city,ordered.knockout_matches,left=ordered.group,label='Knockout incl. third-place',color='#e8a04b')
    axes[0].set(xlabel='Allocated matches',title='Match allocation across 16 host cities');axes[0].legend(fontsize=8)
    country[['venue_share_pct','match_share_pct','knockout_share_pct']].plot.bar(ax=axes[1],color=['#90a4ae','#137c8b','#e8a04b'])
    axes[1].set(ylabel='Tournament share (%)',xlabel='',title='Venues and matches by country');axes[1].tick_params(axis='x',rotation=0)
    axes[1].legend(['Venues','All matches','Knockout matches'],fontsize=8)
    fig.suptitle('2026 FIFA World Cup | Host allocation, not attendance',fontsize=15)
    fig.text(.02,.01,'Sources: FIFA, US EPA, City of Toronto, MLS. Row-level URLs in data/venues.csv.',fontsize=8)
    fig.tight_layout(rect=[0,.04,1,.95]);fig.savefig(out/'host_allocation.png',dpi=160);plt.close(fig)
    print(json.dumps(summary,indent=2));return df,country,summary

if __name__=='__main__': main()
