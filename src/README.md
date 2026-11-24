# how the figures are made

Every figure on the profile page is a plain SVG file. GitHub runs no JavaScript in a README, so all the motion is CSS keyframes and SMIL animation, and every file is written by the Python scripts in this folder. Text is converted to outlines, so nothing depends on fonts being available.

### fig. 1 · potential flow past a greeting

An ideal fluid has a stream function ψ that satisfies the Laplace equation ∇²ψ = 0. `hero.py` solves it on an 861 × 236 grid with the letters as solid bodies, picks a constant for each body so that none of them carries circulation, and traces contour lines of ψ. Those contours are the streamlines. The solve runs three times with the letters at 40%, 72% and full size, and the SVG morphs straight lines through those three fields, so the text shows up as the place the fluid refuses to go.

### fig. 2 · bidirectional bfs

`maze.py` builds a random maze with Kruskal's algorithm and knocks out a few extra walls so there are loops. Two breadth first searches start at opposite ends and stop the moment their frontiers touch, then the shortest path is drawn from the meeting point outward. Each BFS layer is one merged shape with its own timing. A scheduled workflow draws a new maze every day, seeded by the date.

### fig. 3 · a globe without a 3D engine

Each latitude ring of land dots is a flat circle. Spinning a circle and then squashing it vertically is exactly what an orthographic camera does to a ring on a turning sphere, so the whole globe is 57 rotate animations, one per ring. The hidden half of every ring lies on the far side of a straight cut line, so a single clip rectangle per ring takes care of it.

### fig. 4 · one request after another

`stack.py` draws a Spring Boot app as its real request path. A request leaves the client every two seconds, stops at the security filter chain, the controller, the service and the repository, hits the database, and the response rides back on the lower lane. Every request shares the same two second beat, so each box needs just one flashing animation.

### rebuild

```sh
pip install -r src/requirements.txt
python src/build_all.py
```

Fonts are [Unbounded](https://github.com/googlefonts/unbounded) and [Geist Mono](https://github.com/vercel/geist-font), both under the SIL Open Font License. Land outlines come from Natural Earth through [world-atlas](https://github.com/topojson/world-atlas).
