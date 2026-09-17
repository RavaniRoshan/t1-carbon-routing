#import "@preview/akatable:0.1.0": academic-table
#academic-table([Headline results (Azure 40k).],
  (
    [LDP (ours)], [0.0076 [0.0075, 0.0077]], [0.17%], [140.7], [--],
    [Round-robin], [0.0121 [0.0121, 0.0121]], [0.57%], [117.7], [0.0],
    [Least-RTT], [0.0205 [0.0205, 0.0205]], [95.07%], [15258.6], [0.0],
    [Latency-only], [0.0167 [0.0166, 0.0169]], [0.13%], [106.0], [0.0],
    [C-blind SLO], [0.0167 [0.0166, 0.0169]], [0.13%], [106.0], [0.0]
  ),
  format: "ieee", header: ([Policy], [gCO2e/1k], [Viol], [p99 ms], [p],),
  label: <tab:rq2>, columns: 5, align: center, inset: 4pt)
