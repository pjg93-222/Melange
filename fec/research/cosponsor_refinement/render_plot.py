"""Standalone scientific plot; may use the bundled document Python runtime."""
import datetime as dt
import json
from pathlib import Path
import sys

OUT=Path(__file__).resolve().parents[3]/'outputs/cosponsor_refinement_20260905'
sys.path.insert(0,str(OUT/'plot_vendor'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np

def run():
    models=json.loads((OUT/'extension_results.json').read_text(encoding='utf-8'))['models']
    models['lambdamart_network']=json.loads((OUT/'network_ranker_results.json').read_text(encoding='utf-8'))
    fig,ax=plt.subplots(figsize=(9,5.5),layout='constrained')
    for name,color,label in [('boosted_public_coverage','#666666','Public coverage'),('boosted_network','#087e8b','+ Member networks'),('logistic_all','#aa4b00','All-context logistic'),('lambdamart_network','#7156a5','Network LambdaMART')]:
        curve=[s for s in models[name]['selective_2024'] if s['target_retained_2023']>=.05]
        xx=np.array([s['recommendations_2024'] for s in curve]);yy=np.array([s['precision_2024'] for s in curve])
        ax.plot(xx,yy,'o-',label=label,color=color,markersize=4)
    ax.set_xscale('log');ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set(xlabel='Recommendations retained in 2024 (log scale)',ylabel='Correct subsequent joins / recommendations',
        title='Higher precision requires fewer recommendations\n2023 cutoffs applied unchanged to 2024 development forecasts',ylim=(0,.15))
    ax.grid(alpha=.2);ax.legend(frameon=False);fig.savefig(OUT/'precision_coverage.png',dpi=180);fig.savefig(OUT/'precision_coverage.svg');plt.close(fig)
    (OUT/'plot_runtime.json').write_text(json.dumps(dict(rendered_utc=dt.datetime.now(dt.timezone.utc).isoformat(),python=sys.version,matplotlib=matplotlib.__version__,numpy=np.__version__),indent=2),encoding='utf-8')


if __name__=='__main__':run()
