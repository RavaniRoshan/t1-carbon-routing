#import "@preview/cetz:0.5.2"
#import "@preview/cetz-plot:0.1.4": plot
#cetz.canvas({
  plot.plot(size: (7.2, 4.2),
    x-label: [p99 TTFT (ms)], y-label: [gCO2e/1k tok],
    y-min: 0.0071, y-max: 0.0081,
    y-ticks: ((0.0072, [0.0072]), (0.0074, [0.0074]), (0.0076, [0.0076]), (0.0078, [0.0078])), y-tick-step: none,
    legend: auto, {
    plot.add(((99.6, 0.0078), (117.6, 0.0077), (137.0, 0.0076), (176.3, 0.0074),), mark: "o", label: [frontier])
  })
})
