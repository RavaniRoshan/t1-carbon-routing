#figure(
  table(columns: 5, align: center,
    table.header([Policy], [gCO2e/1k], [Viol], [p99 TTFT ms], [p vs LDP]),
    [LDP (ours)], [0.007603 [0.007468, 0.007737]], [0.17%], [140.690202], [--],
    [Round-robin], [0.012138 [0.012138, 0.012138]], [0.57%], [117.725958], [0.0],
    [Least-RTT], [0.020514 [0.020514, 0.020514]], [95.07%], [15258.593228], [0.0],
    [Latency-only], [0.016741 [0.016591, 0.016891]], [0.13%], [106.028924], [0.0],
    [Carbon-blind SLO], [0.016741 [0.016591, 0.016891]], [0.13%], [106.028924], [0.0]
  ),
  caption: [Headline: gCO2e/1k tokens, violation rate, p99 TTFT (Azure 40k, N=30).],
) <tab:rq2>
