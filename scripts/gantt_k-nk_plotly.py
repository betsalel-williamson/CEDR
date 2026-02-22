"""
Interactive Gantt chart using Plotly.

Same input as gantt_k-nk.py (ZCU102 trace CSV). Produces an interactive HTML chart
with zoom, pan, hover tooltips, and legend click-to-toggle. Intended for daemon-based
execution with streaming enabled; plots all frames of a given application.
"""
import csv
import argparse
import sys
from collections import namedtuple

import plotly.graph_objects as go

ScheduleEvent = namedtuple('ScheduleEvent', 'job task start end proc id_string')

# Match gantt_k-nk.py color scheme (task % 5)
COLOR_CHOICES = ['firebrick', 'midnightblue', 'lightskyblue', 'dodgerblue', 'green']
TASK_TYPE_LABELS = [f'TASK_ID ({(i)}+5n)' for i in range(5)]


def load_proc_schedules(input_path):
    """
    Parse trace CSV into proc_schedules dict, matching gantt_k-nk.py logic exactly.
    Returns (proc_schedules, start_offset).
    """
    with open(input_path, newline='', encoding='utf-8') as f:
        lines = f.readlines()
    lines_parsed = [(x.strip()).split(", ") for x in lines]
    start = sys.maxsize
    for elem in lines_parsed:
        start = min(start, int((elem[5].split(": "))[1]))

    proc_schedules = {}
    with open(input_path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            job_id = row[0].split(':')[1].strip()
            job_name = row[1].split(':')[1].strip()
            task_id = row[2].split(':')[1].strip()
            task_name = row[3].split(':')[1].strip()
            proc_name = row[4].split(':')[1].strip()
            start_time = row[5].split(':')[1].strip()
            end_time = row[6].split(':')[1].strip()
            task_identifier = job_name + '_' + job_id + '-' + task_name
            schedule_event = ScheduleEvent(
                int(job_id), int(task_id),
                (int(start_time) - start), (int(end_time) - start),
                proc_name, task_identifier
            )
            if proc_name in proc_schedules:
                proc_schedules[proc_name].append(schedule_event)
            else:
                proc_schedules[proc_name] = [schedule_event]

    return proc_schedules, start


def build_timeline_df(proc_schedules):
    """Build list of dicts with Start/Finish in ms and task type, for Bar traces."""
    processors = sorted(proc_schedules.keys())
    rows = []
    for proc in processors:
        for job in proc_schedules[proc]:
            start_ms = job.start / 1e6
            finish_ms = job.end / 1e6
            task_type = job.task % 5
            rows.append({
                'Processor': proc,
                'Start': start_ms,
                'Finish': finish_ms,
                'Duration_ms': finish_ms - start_ms,
                'TaskType': task_type,
                'TaskTypeLabel': TASK_TYPE_LABELS[task_type],
                'TaskId': job.id_string,
                'Job': job.job,
                'Task': job.task,
            })
    return rows


def show_gantt_plotly(proc_schedules, output_html='gantt.html', output_png=None):
    """
    Build and save an interactive Plotly Gantt chart from proc_schedules.
    Uses go.Bar (horizontal bars with base=start, x=duration) so the x-axis is
    linear Time (ms). px.timeline would interpret numeric values as datetimes.
    """
    rows = build_timeline_df(proc_schedules)
    if not rows:
        sys.stderr.write("No schedule events to plot.\n")
        return

    processors = sorted(proc_schedules.keys())

    fig = go.Figure()
    for task_type in range(5):
        subset = [r for r in rows if r['TaskType'] == task_type]
        if not subset:
            # Empty category (e.g. no TASK_ID 4+5n): legend entry only, no bar
            fig.add_trace(go.Bar(
                x=[], y=[], base=[], orientation='h',
                name=TASK_TYPE_LABELS[task_type],
                marker_color=COLOR_CHOICES[task_type],
                showlegend=True,
                legendgroup=TASK_TYPE_LABELS[task_type],
            ))
            continue
        fig.add_trace(go.Bar(
            x=[r['Duration_ms'] for r in subset],
            y=[r['Processor'] for r in subset],
            base=[r['Start'] for r in subset],
            orientation='h',
            name=TASK_TYPE_LABELS[task_type],
            marker_color=COLOR_CHOICES[task_type],
            legendgroup=TASK_TYPE_LABELS[task_type],
            customdata=[[r['TaskId'], r['Job'], r['Task'], round(r['Duration_ms'], 2), r['Start'], r['Finish']] for r in subset],
            hovertemplate=(
                '<b>%{y}</b><br>'
                'TaskId: %{customdata[0]}<br>'
                'Job: %{customdata[1]} | Task: %{customdata[2]}<br>'
                'Duration: %{customdata[3]} ms<br>'
                'Start: %{customdata[4]:.2f} ms | Finish: %{customdata[5]:.2f} ms<extra></extra>'
            ),
        ))

    fig.update_layout(
        title='Gantt chart (ZCU102 runtime)',
        xaxis_title='Time (ms)',
        yaxis_title='Processor',
        barmode='overlay',
        xaxis=dict(
            type='linear',
            showgrid=True,
            gridcolor='rgba(0,128,0,0.3)',
            zeroline=False,
        ),
        yaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=processors,  # match Matplotlib: first processor at bottom
            showgrid=False,
        ),
        legend=dict(
            title='Task type',
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
        ),
        dragmode='zoom',
        font=dict(size=14),
        margin=dict(b=60, t=80),
    )
    fig.write_html(output_html)
    print(f"Wrote interactive chart to {output_html}")

    if output_png:
        try:
            fig.write_image(output_png)
            print(f"Wrote static PNG to {output_png}")
        except Exception as e:
            sys.stderr.write(f"Could not write PNG (install kaleido: pip install kaleido): {e}\n")


def generate_argparser():
    parser = argparse.ArgumentParser(
        description="Interactive Gantt chart from ZCU102 trace (Plotly). Same input as gantt_k-nk.py."
    )
    parser.add_argument("inputFile", help="Input trace file to be plotted as a Gantt chart")
    parser.add_argument(
        '-o', '--output',
        default='gantt.html',
        metavar='FILE',
        help="Output HTML file (default: gantt.html)",
    )
    parser.add_argument(
        '--png',
        default=None,
        metavar='FILE',
        help="Also write a static PNG to FILE (requires kaleido)",
    )
    return parser


if __name__ == '__main__':
    argparser = generate_argparser()
    args = argparser.parse_args()

    proc_schedules, _ = load_proc_schedules(args.inputFile)
    show_gantt_plotly(
        proc_schedules,
        output_html=args.output,
        output_png=args.png,
    )
