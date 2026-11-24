"""Redraw every figure in assets/. Run from anywhere with  python src/build_all.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stack
import globe
import hero
import intro
import links
import maze

if __name__ == "__main__":
    hero.render()
    intro.build()
    maze.daily()
    globe.build()
    stack.build()
    links.build()
