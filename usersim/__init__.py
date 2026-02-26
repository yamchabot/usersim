"""
usersim — user simulation framework

Measure whether your application satisfies simulated user personas
by expressing their needs as Z3 constraint formulas.

Quick start
-----------
  pip install usersim
  usersim init
  # edit instrumentation, perceptions.py, users/
  usersim judge --perceptions perceptions.json --users users/*.py

Layers
------
  Instrumentation  your app language → metrics.json
  Perceptions      any language      → perceptions.json
  Judgement        Z3 (Python)       → results.json

See https://github.com/yamchabot/usersim for docs and examples.
"""

from usersim.judgement.person import Person, FactNamespace

__all__ = ["Person", "FactNamespace"]
__version__ = "0.1.0"
