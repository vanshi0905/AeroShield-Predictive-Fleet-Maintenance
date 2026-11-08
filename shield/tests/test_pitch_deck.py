"""Unit tests for PowerPoint pitch deck generator (scripts/generate_pitch_deck.py)."""

import os
import pytest
import pptx
from scripts.generate_pitch_deck import build_presentation, OUTPUT_PATH


def test_build_presentation_generates_valid_pptx(tmp_path):
    """Verify that build_presentation generates a valid 8-slide presentation."""
    build_presentation()
    assert os.path.exists(OUTPUT_PATH), f"Expected presentation file at {OUTPUT_PATH}"
    assert os.path.getsize(OUTPUT_PATH) > 10_000, "Presentation file is unexpectedly small"

    prs = pptx.Presentation(OUTPUT_PATH)
    assert len(prs.slides) == 8, f"Expected exactly 8 slides, found {len(prs.slides)}"


def test_pitch_deck_widescreen_and_slide_contents():
    """Verify widescreen 16:9 dimensions and that every slide contains text content."""
    prs = pptx.Presentation(OUTPUT_PATH)
    # 16:9 aspect ratio: 13.333 x 7.5 inches
    assert round(prs.slide_width.inches, 2) == 13.33
    assert round(prs.slide_height.inches, 2) == 7.50

    for i, slide in enumerate(prs.slides, start=1):
        text_shapes = [shape for shape in slide.shapes if shape.has_text_frame and shape.text_frame.text.strip()]
        assert len(text_shapes) >= 1, f"Slide {i} has no non-empty text shapes"
