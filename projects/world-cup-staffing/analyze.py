"""SQLite joins and window functions for a hypothetical staffing budget."""
from pathlib import Path
import sqlite3,json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent

def main():
    venues=pd.read_csv(ROOT.parent/'world-cup-host-allocation/data/venues.csv')
    stages=['group','round32','round16','quarterfinal','semifinal','third_place','final']
    inventory=venues.melt(id_vars=['city','country'],value_vars=stages,var_name='stage',value_name='matches')
    assumptions=pd.read_csv(ROOT/'data/stage_assumptions.csv')
    scenarios=pd.read_csv(ROOT/'data/scenarios.csv')
    assert assumptions.stage.is_unique and set(assumptions.stage)==set(stages)
    assert scenarios.scenario.is_unique and scenarios.staff_multiplier.gt(0).all()
    assert (assumptions[['staff_per_match','hours_per_shift','hourly_rate_cad']]>0).all().all()
    assert not assumptions.isna().any().any() and not scenarios.isna().any().any()
    assert inventory.matches.sum()==104 and len(venues)==16 and venues.city.is_unique
    with sqlite3.connect(':memory:') as db:
        inventory.to_sql('match_inventory',db,index=False)
        assumptions.to_sql('stage_assumptions',db,index=False)
        scenarios.to_sql('scenarios',db,index=False)
        result=pd.read_sql_query((ROOT/'queries.sql').read_text(),db)
    assert len(result)==16*len(scenarios)
    assert result.groupby('scenario').matches.sum().eq(104).all()
    # Independent pandas calculation catches join duplication and formula errors.
    expected=inventory.merge(assumptions,on='stage',validate='many_to_one').merge(scenarios,how='cross')
    expected['cost']=expected.matches*np.ceil(expected.staff_per_match*expected.staff_multiplier)*expected.hours_per_shift*expected.hourly_rate_cad
    totals=result.groupby('scenario').labor_cost_cad.sum()
    assert np.allclose(totals.sort_index(),expected.groupby('scenario').cost.sum().sort_index())
    country=result.groupby(['scenario','country'])[['matches','staff_shifts','staff_hours','labor_cost_cad']].sum().reset_index()
    base=result.loc[result.scenario.eq('base')]
    van=base.loc[base.city.eq('Vancouver')].iloc[0]
    summary={'basis':'illustrative staffing assumptions, not actual costs','scenario_totals_cad':totals.to_dict(),
      'base_vancouver_cad':float(van.labor_cost_cad),'base_vancouver_staff_hours':float(van.staff_hours),
      'highest_base_cost_city':base.iloc[0].city,'highest_base_cost_cad':float(base.iloc[0].labor_cost_cad)}
    out=ROOT/'results';out.mkdir(exist_ok=True)
    result.to_csv(out/'city_scenarios.csv',index=False);country.to_csv(out/'country_scenarios.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    fig,axs=plt.subplots(1,2,figsize=(13,7))
    ordered=base.sort_values('labor_cost_cad')
    axs[0].barh(ordered.city,ordered.labor_cost_cad/1e6,color=['#e4a342' if c=='Vancouver' else '#167d8d' for c in ordered.city])
    axs[0].set(xlabel='Illustrative labor cost (CAD millions)',title='Base assumptions by host city')
    totals.reindex(['low','base','high']).div(1e6).plot.bar(ax=axs[1],color=['#aab3b7','#167d8d','#e4a342'],rot=0)
    axs[1].set(xlabel='Staffing scenario',ylabel='Illustrative labor cost (CAD millions)',title='Tournament-wide sensitivity')
    fig.suptitle('World Cup staffing budget | Hypothetical assumptions, not actual spending')
    fig.text(.02,.01,'Inventory: official host allocation sources. Staffing, shift length, and CAD wage are analyst-selected assumptions.',fontsize=8)
    fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(out/'staffing_scenarios.png',dpi=140);plt.close(fig)
    print(json.dumps(summary,indent=2));return result,summary

if __name__=='__main__':main()
