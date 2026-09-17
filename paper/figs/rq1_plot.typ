#import "@preview/cetz:0.5.2"
#import "@preview/cetz-plot:0.1.4": plot
#cetz.canvas({
  plot.plot(size: (7.2, 4.2),
    x-label: [Batch size], y-label: [J/token],
    x-min: -0.5, x-max: 4.5,
    x-ticks: ((0, [1]), (2, [4]), (4, [16])), x-tick-step: none,
    legend: auto, {
    plot.add(((0, 1.393), (2, 0.3713), (4, 0.1432),), mark: "o", label: [C=128])
    plot.add(((0, 1.5055), (2, 0.5782), (4, 0.204),), mark: "o", label: [C=512])
  })
})
