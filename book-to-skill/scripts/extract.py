#!/usr/bin/env python3
"""
Extract text from a document file for book-to-skill processing.
Modular entrypoint wrapper.
"""

import os
import sys

# Ensure the scripts/ directory (where the 'extractor' package lives) is in sys.path
# so the modular package can be imported reliably regardless of the working directory.
sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))

from extractor.utils import main

if __name__ == "__main__":
    main()
