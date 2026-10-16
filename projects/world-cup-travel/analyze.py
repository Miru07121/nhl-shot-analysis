"""Exhaustive optimization of a hypothetical six-city visit itinerary."""
from pathlib import Path
from itertools import permutations
import json, math
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent

def haversine(a,b):
    lat1,lon1,lat2,lon2=map(math.radians,[*a,*b])
    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371.0088*2*math.asin(math.sqrt(min(1,max(0,h))))

def main():
    cities=pd.read_csv(ROOT/'data/cities.csv').set_index('city')
    assert len(cities)==6 and cities.index.is_unique and not cities.isna().any().any()
    assert cities.latitude.between(-90,90).all() and cities.longitude.between(-180,180).all()
    points={k:(r.latitude,r.longitude) for k,r in cities.iterrows()}
    matrix=pd.DataFrame({b:{a:haversine(points[a],points[b]) for a in points} for b in points})
    assert np.allclose(matrix,matrix.T) and np.allclose(np.diag(matrix),0)
    assert abs(haversine((0,0),(0,90))-math.pi*6371.0088/2)<1e-8
    config=json.loads((ROOT/'data/scenario.json').read_text())
    baseline=config['baseline']; start=baseline[0];end=baseline[-1]
    assert len(baseline)==len(set(baseline))==6 and set(baseline)==set(points)
    def length(route):return sum(matrix.loc[a,b] for a,b in zip(route,route[1:]))
    routes=[]
    for middle in permutations(baseline[1:-1]):
        route=[start,*middle,end]
        routes.append({'route':' → '.join(route),'distance_km':length(route)})
    ranked=pd.DataFrame(routes).sort_values(['distance_km','route']).reset_index(drop=True)
    assert len(ranked)==math.factorial(4)
    best=ranked.iloc[0];best_route=best.route.split(' → ')
    original=length(baseline);saved=original-best.distance_km
    summary={'scenario':'hypothetical city visits; no match-date constraints','routes_evaluated':len(ranked),
        'baseline_route':baseline,'shortest_route':best_route,'baseline_km':original,
        'shortest_km':float(best.distance_km),'distance_reduction_km':saved,'distance_reduction_pct':saved/original*100,
        'median_route_km':float(ranked.distance_km.median())}
    out=ROOT/'results';out.mkdir(exist_ok=True)
    matrix.to_csv(out/'distance_matrix_km.csv');ranked.to_csv(out/'all_routes.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    fig,axs=plt.subplots(1,2,figsize=(13,6))
    for route,label,color in [(baseline,'Illustrative baseline','#bb654e'),(best_route,'Shortest of 24 routes','#167d8d')]:
        axs[0].plot([points[c][1] for c in route],[points[c][0] for c in route],'-o',label=label,color=color,alpha=.75)
    for city,(lat,lon) in points.items():axs[0].annotate(city,(lon,lat),xytext=(4,6),textcoords='offset points',fontsize=8)
    axs[0].set(xlabel='Longitude',ylabel='Latitude',title='City-coordinate schematic (not a flight map)')
    axs[0].margins(.15);axs[0].legend(fontsize=8)
    axs[1].bar(['Baseline','Median of 24','Shortest'],[original,ranked.distance_km.median(),best.distance_km],color=['#bb654e','#aab3b7','#167d8d'])
    axs[1].set(ylabel='Sum of great-circle distances (km)',title=f'Hypothetical baseline reduction: {saved/original:.1%}')
    fig.suptitle('World Cup host-city travel | Hypothetical six-city route comparison')
    fig.text(.02,.01,'City coordinates: GeoNames (CC BY 4.0). No schedules, air routes, prices, stadium transfers or actual team travel modeled.',fontsize=8)
    fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(out/'travel_routes.png',dpi=140);plt.close(fig)
    print(json.dumps(summary,indent=2,ensure_ascii=False));return ranked,summary

if __name__=='__main__':main()
