"""
Interactive Gantt chart using Plotly.

Same input as gantt_k-nk.py (ZCU102 trace CSV). Produces an interactive HTML chart
with zoom, pan, hover tooltips, and legend click-to-toggle. Intended for daemon-based
execution with streaming enabled; plots all frames of a given application.
"""
import argparse
import sys
import threading
import time


class Spinner:
    """Show an indeterminate spinner on stderr. Message is updatable. Clears the line on exit."""

    CHARS = ['|', '/', '-', '\\']

    def __init__(self, message='Working...', stream=None):
        self.message = message
        self.stream = stream or sys.stderr
        self._stop = threading.Event()
        self._thread = None
        self._had_other_output = False  # set True if stderr/stdout used so we clear the line above

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            msg = self.message  # read current message each tick
            c = self.CHARS[i % len(self.CHARS)]
            self.stream.write('\r  {} {}'.format(c, msg))
            self.stream.flush()
            i += 1
            self._stop.wait(0.08)

    def __enter__(self):
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        time.sleep(0.03)  # Brief pause so first frame is visible
        return self

    def __exit__(self, *args):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        # Clear spinner line so it disappears
        if self._had_other_output:
            self.stream.write('\033[A\r\033[K')  # move up one line, then clear
        else:
            self.stream.write('\r\033[K')  # cursor still on spinner line
        self.stream.flush()
        return False

# Match gantt_k-nk.py color scheme (task % 5)
COLOR_CHOICES = ['firebrick', 'midnightblue', 'lightskyblue', 'dodgerblue', 'green']
TASK_TYPE_LABELS = [f'TASK_ID ({(i)}+5n)' for i in range(5)]


def load_trace(input_path):
    """
    Load ZCU102 trace CSV into a plot-ready DataFrame.
    Trace format: no header; each row has "Key: value" fields separated by ", ".
    We use the first 7 fields by position (key names may be e.g. app_id, app_name,
    task_id, task_name, resource_name, ref_start_time, ref_stop_time).
    Returns DataFrame with Processor, Start, Finish, Duration_ms, TaskType,
    TaskTypeLabel, TaskId, Job, Task.
    """
    # Single-char sep=',' for C engine speed; trace has 10 comma-separated fields, we use first 7.
    raw = pd.read_csv(input_path, header=None, encoding='utf-8', sep=',')
    if raw.empty:
        return pd.DataFrame(columns=[
            'Processor', 'Start', 'Finish', 'Duration_ms',
            'TaskType', 'TaskTypeLabel', 'TaskId', 'Job', 'Task'
        ])
    # Use first 7 columns only (Job, Name, Task, Task name, Proc, Start, End).
    raw = raw.iloc[:, :7]

    def extract_value(ser):
        return ser.astype(str).str.split(': ', n=1).str.get(1).str.strip()

    raw.columns = ['Job', 'Name', 'Task', 'TaskName', 'Proc', 'Start', 'End']
    df = pd.DataFrame()
    df['Job'] = extract_value(raw['Job']).astype(int)
    df['Name'] = extract_value(raw['Name'])
    df['Task'] = extract_value(raw['Task']).astype(int)
    df['TaskName'] = extract_value(raw['TaskName'])
    df['Processor'] = extract_value(raw['Proc'])
    df['Start_ns'] = extract_value(raw['Start']).astype(int)
    df['End_ns'] = extract_value(raw['End']).astype(int)

    start_offset = df['Start_ns'].min()
    df['Start'] = (df['Start_ns'] - start_offset) / 1e6
    df['Finish'] = (df['End_ns'] - start_offset) / 1e6
    df['Duration_ms'] = df['Finish'] - df['Start']
    df['TaskType'] = df['Task'] % 5
    df['TaskTypeLabel'] = df['TaskType'].map(lambda i: TASK_TYPE_LABELS[i])
    df['TaskId'] = df['Name'] + '_' + df['Job'].astype(str) + '-' + df['TaskName']

    return df[['Processor', 'Start', 'Finish', 'Duration_ms', 'TaskType', 'TaskTypeLabel', 'TaskId', 'Job', 'Task']]


def show_gantt_plotly(df, output_html='gantt.html', output_png=None):
    """
    Build and save an interactive Plotly Gantt chart from a plot-ready DataFrame.
    Uses go.Bar (horizontal bars with base=start, x=duration) so the x-axis is
    linear Time (ms). px.timeline would interpret numeric values as datetimes.
    """
    if df.empty:
        sys.stderr.write("No schedule events to plot.\n")
        return

    processors = sorted(df['Processor'].unique())

    fig = go.Figure()
    for task_type in range(5):
        subset = df[df['TaskType'] == task_type]
        if subset.empty:
            # Empty category (e.g. no TASK_ID 4+5n): legend entry only, no bar
            fig.add_trace(go.Bar(
                x=[], y=[], base=[], orientation='h',
                name=TASK_TYPE_LABELS[task_type],
                marker_color=COLOR_CHOICES[task_type],
                showlegend=True,
                legendgroup=TASK_TYPE_LABELS[task_type],
            ))
            continue
        customdata = list(zip(
            subset['TaskId'], subset['Job'], subset['Task'],
            subset['Duration_ms'].round(2), subset['Start'], subset['Finish']
        ))
        fig.add_trace(go.Bar(
            x=subset['Duration_ms'].tolist(),
            y=subset['Processor'].tolist(),
            base=subset['Start'].tolist(),
            orientation='h',
            name=TASK_TYPE_LABELS[task_type],
            marker_color=COLOR_CHOICES[task_type],
            legendgroup=TASK_TYPE_LABELS[task_type],
            customdata=customdata,
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
    png_path = None
    if output_png:
        try:
            fig.write_image(output_png)
            png_path = output_png
        except Exception as e:
            sys.stderr.write(f"Could not write PNG (install kaleido: pip install kaleido): {e}\n")
    return output_html, png_path


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

    # Spinner covers imports + load + build (pandas/plotly are heavy; defer so spinner shows first)
    with Spinner('Loading trace...') as spinner:
        import pandas as pd
        import plotly.graph_objects as go
        # Inject so load_trace / show_gantt_plotly see them
        globals()['pd'] = pd
        globals()['go'] = go
        df = load_trace(args.inputFile)

        if df.empty:
            spinner._had_other_output = True
            sys.stderr.write('No schedule events to plot.\n')
            sys.exit(1)

        spinner.message = 'Building chart...'
        output_html, output_png_written = show_gantt_plotly(
            df,
            output_html=args.output,
            output_png=args.png,
        )
    print(f"Wrote interactive chart to {output_html}")
    if output_png_written:
        print(f"Wrote static PNG to {output_png_written}")
