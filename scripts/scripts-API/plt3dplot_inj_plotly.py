"""
Interactive 3D DSE plot using Plotly.

Same input as plt3dplot_inj.py (CSV from makedataframe.py). Produces an interactive
HTML 3D scatter with zoom, pan, hover tooltips, and legend click-to-toggle.
Optionally writes a static PNG (requires kaleido).
"""
import argparse
import sys

import pandas as pd
import plotly.graph_objects as go

# Match matplotlib script: one color per scheduler (tab10-like)
SCHED_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


def generate_argparser():
    parser = argparse.ArgumentParser(
        description="Plot a 3D DSE plot from CSV file (Plotly). Same input as plt3dplot_inj.py."
    )
    parser.add_argument("inputFile", help="Input CSV file to plot")
    parser.add_argument(
        "metricSelect",
        help="Select which metric to plot on Z-axis: CUMU, EXEC, or SCHED",
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        metavar='FILE',
        help="Output HTML file (default: dse_<metric>.html)",
    )
    parser.add_argument(
        '--png',
        default=None,
        metavar='FILE',
        help="Also write a static PNG to FILE (requires kaleido)",
    )
    return parser


def build_configlist(CPUS, FFTS, MMULTS, ZIPS, GPUS):
    configlist = []
    configlist_tick = []
    for c in range(CPUS - 1, CPUS):
        for f in range(FFTS + 1):
            for m in range(MMULTS + 1):
                for z in range(ZIPS + 1):
                    for g in range(GPUS + 1):
                        if GPUS == 0:
                            configlist.append('C' + str(c + 1) + '+F' + str(f) + '+M' + str(m) + '+Z' + str(z))
                            configlist_tick.append('C' + str(c + 1) + '\nF' + str(f) + '\nM' + str(m) + '\nZ' + str(z))
                        else:
                            configlist.append('C' + str(c + 1) + '+F' + str(f) + '+M' + str(m) + '+Z' + str(z) + '+G' + str(g))
                            configlist_tick.append('C' + str(c + 1) + '\nG' + str(g))
    return configlist, configlist_tick


def main():
    argparser = generate_argparser()
    args = argparser.parse_args()

    ### Configuration specification (match plt3dplot_inj.py) ###
    CPUS = 3
    FFTS = 2
    MMULTS = 0
    ZIPS = 2
    GPUS = 0
    TRIALS = 2
    schedlist = {'SIMPLE': 1, 'MET': 2, 'ETF': 3}
    schednamelist = ['RR', 'MET', 'ETF']

    metrics = [
        'Avg. cumulative execution time / app. (ns)',
        'Avg. execution time / app.(ns)',
        'Avg. Scheduling overhead / app.(ns)',
    ]
    metricnames = [
        'Avg. Cumulative Execution Time / App. (ms)',
        'Avg. Execution Time / App. (ms)',
        'Avg. Scheduling Overhead / App. (ms)',
    ]

    metricSelect = args.metricSelect
    if metricSelect == 'CUMU':
        metricselect = 0
    elif metricSelect == 'EXEC':
        metricselect = 1
    elif metricSelect == 'SCHED':
        metricselect = 2
    else:
        print("Invalid metric '", metricSelect, "' selected, please select from [CUMU, EXEC, SCHED]", file=sys.stderr)
        sys.exit(1)

    configlist, configlist_tick = build_configlist(CPUS, FFTS, MMULTS, ZIPS, GPUS)

    df = pd.read_csv(args.inputFile, sep=',')
    metric_col = metrics[metricselect]

    fig = go.Figure()

    for sched in schedlist.keys():
        x_vals, y_vals, z_vals = [], [], []
        configcount = 1
        for config in configlist:
            df_rp = df.loc[df['Resource Pool'] == config]
            df_rp_sc = df_rp.filter(items=['Scheduler', 'Injection Rate (Mbps)', metric_col])
            inj_rates = sorted(df_rp_sc['Injection Rate (Mbps)'].unique().tolist())

            for inj in inj_rates:
                row = df_rp_sc.loc[
                    (df_rp_sc['Scheduler'] == sched) & (df_rp_sc['Injection Rate (Mbps)'] == inj)
                ]
                if row.empty:
                    continue
                z_ns = row[metric_col].values[0]
                z_ms = z_ns / 1e6
                x_vals.append(inj)
                y_vals.append(configcount)
                z_vals.append(z_ms)
            configcount += 1

        if not x_vals:
            continue

        color_idx = (schedlist[sched] - 1) % len(SCHED_COLORS)
        name = schednamelist[schedlist[sched] - 1]
        fig.add_trace(go.Scatter3d(
            x=x_vals,
            y=y_vals,
            z=z_vals,
            mode='markers',
            name=name,
            marker=dict(
                size=8,
                color=SCHED_COLORS[color_idx],
                opacity=1,
            ),
            hovertemplate=(
                '<b>%{fullData.name}</b><br>'
                'Injection Rate: %{x} Mbps<br>'
                'Config index: %{y}<br>'
                'Value: %{z:.4f} ms<extra></extra>'
            ),
        ))

    # Y-axis: use config indices 1..configcount-1; tick labels from configlist_tick
    y_tick_vals = list(range(1, len(configlist) + 1))
    x_max = max(
        df['Injection Rate (Mbps)'].max() if not df.empty else 20,
        1,
    )

    fig.update_layout(
        title=f'DSE 3D – {metricnames[metricselect]}',
        scene=dict(
            xaxis_title='Injection Rate (Mbps)',
            yaxis_title='Hardware Configurations',
            zaxis_title=metricnames[metricselect],
            xaxis=dict(
                dtick=x_max / 4 if x_max >= 4 else 1,
                showgrid=True,
                gridcolor='rgba(128,128,128,0.2)',
            ),
            yaxis=dict(
                tickmode='array',
                tickvals=y_tick_vals,
                ticktext=configlist_tick,
                showgrid=True,
                gridcolor='rgba(128,128,128,0.2)',
            ),
            zaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
        ),
        legend=dict(
            title='Scheduler',
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
        ),
        font=dict(size=14),
        margin=dict(l=0, r=0, b=0, t=60),
    )

    out_html = args.output or f"dse_{metricSelect}.html"
    fig.write_html(out_html)
    print(f"Wrote interactive chart to {out_html}")

    png_path = args.png
    if png_path:
        try:
            fig.write_image(png_path)
            print(f"Wrote static PNG to {png_path}")
        except Exception as e:
            sys.stderr.write(f"Could not write PNG (install kaleido: pip install kaleido): {e}\n")


if __name__ == '__main__':
    main()
