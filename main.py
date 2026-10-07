"""Script d'entrée rétrocompatible pour la veille journalière.

Redirige vers le pipeline du package watch.
"""

from watch.pipeline import main

if __name__ == "__main__":
    main()
