"""Test size resolution and validation."""
import typing
from fractions import Fraction

import pytest

from hermes_post_design.chiyi_core import (
    DEFAULT_SIZE,
    MAX_CUSTOM_DIMENSION,
    MAX_UPSTREAM_PIXELS,
    MIN_CUSTOM_SHORT_EDGE,
    MIN_OUTPUT_SHORT_EDGE,
    MIN_UPSTREAM_PIXELS,
    SIZE_MULTIPLE,
    SizePlan,
    resolve_size,
)


class TestTypeAnnotations:
    """Verify public API type annotations are strict, not Any."""

    def test_resolve_size_has_strict_annotations(self):
        """resolve_size must use strict types: str -> SizePlan, never Any."""
        hints = typing.get_type_hints(resolve_size)
        # Check parameter annotation (first positional parameter)
        params = list(hints.keys())
        assert 'size' in params, "resolve_size must have 'size' parameter"
        assert hints['size'] is str, f"size parameter must be str, got {hints['size']}"
        # Check return annotation
        assert 'return' in hints, "resolve_size must have return annotation"
        assert hints['return'] is SizePlan, f"return must be SizePlan, got {hints['return']}"


class TestConstants:
    """Verify sizing constants are exported."""

    def test_default_size(self):
        assert DEFAULT_SIZE == "1024x1024"

    def test_min_output_short_edge(self):
        assert MIN_OUTPUT_SHORT_EDGE == 1024

    def test_min_custom_short_edge(self):
        assert MIN_CUSTOM_SHORT_EDGE == 256

    def test_max_custom_dimension(self):
        assert MAX_CUSTOM_DIMENSION == 3840

    def test_min_upstream_pixels(self):
        assert MIN_UPSTREAM_PIXELS == 655_360

    def test_max_upstream_pixels(self):
        assert MAX_UPSTREAM_PIXELS == 8_294_400

    def test_size_multiple(self):
        assert SIZE_MULTIPLE == 16


class TestBasicResolution:
    """Test basic size resolution cases."""

    def test_default_1024x1024(self):
        result = resolve_size("1024x1024")
        assert result == SizePlan(
            requested="1024x1024",
            upstream="1024x1024",
            target_width=1024,
            target_height=1024,
        )

    def test_portrait_1080x1920_requires_upstream_scaling(self):
        """1080x1920: short edge 1080 needs upstream 1088 (16-aligned)."""
        result = resolve_size("1080x1920")
        assert result.requested == "1080x1920"
        assert result.upstream == "1088x1920"
        assert result.target_width == 1080
        assert result.target_height == 1920

    def test_tiny_256x256_scales_to_min_upstream(self):
        """256x256 valid input, upstream must scale to 1024 short edge."""
        result = resolve_size("256x256")
        assert result.requested == "256x256"
        assert result.upstream == "1024x1024"
        assert result.target_width == 256
        assert result.target_height == 256

    def test_valid_3_to_1_ratio_256x768(self):
        """256x768 is valid 3:1 aspect ratio."""
        result = resolve_size("256x768")
        assert result.requested == "256x768"
        # Upstream: scale = 1024/256 = 4.0, so 256*4=1024, 768*4=3072
        assert result.upstream == "1024x3072"
        assert result.target_width == 256
        assert result.target_height == 768

    def test_max_pixels_boundary_2880x2880(self):
        """2880x2880 = 8,294,400 pixels, exactly at limit."""
        result = resolve_size("2880x2880")
        assert result.requested == "2880x2880"
        # Short edge 2880 > 1024, so scale=1.0, upstream same as requested
        assert result.upstream == "2880x2880"
        assert result.target_width == 2880
        assert result.target_height == 2880


class TestInputNormalization:
    """Test input whitespace and case normalization."""

    def test_strip_leading_whitespace(self):
        result = resolve_size("  1024x1024")
        assert result.requested == "1024x1024"

    def test_strip_trailing_whitespace(self):
        result = resolve_size("1024x1024  ")
        assert result.requested == "1024x1024"

    def test_strip_both_whitespace(self):
        result = resolve_size("  1024x1024  ")
        assert result.requested == "1024x1024"

    def test_uppercase_x_normalized(self):
        result = resolve_size("1024X1024")
        assert result.requested == "1024x1024"

    def test_mixed_case_x_normalized(self):
        result = resolve_size("1080X1920")
        assert result.requested == "1080x1920"


class TestInvalidFormat:
    """Test invalid format inputs raise ValueError."""

    def test_none_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size(None)  # type: ignore

    def test_integer_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size(1024)  # type: ignore

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("")

    def test_word_square_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("square")

    def test_word_4k_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("4K")

    def test_colon_separator_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("1080:1920")

    def test_missing_height_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("1024x")

    def test_missing_width_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("x1024")

    def test_float_width_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("1024.5x1024")

    def test_float_height_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("1024x1024.5")

    def test_negative_width_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("-1024x1024")

    def test_negative_height_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("1024x-1024")

    def test_zero_width_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("0x1024")

    def test_zero_height_raises_value_error(self):
        with pytest.raises(ValueError, match="size must use WIDTHxHEIGHT"):
            resolve_size("1024x0")


class TestBoundaryViolations:
    """Test boundary violations for dimensions and pixels."""

    def test_short_edge_255_rejected(self):
        """Short edge must be at least 256."""
        with pytest.raises(ValueError, match="at least 256"):
            resolve_size("255x1024")

    def test_long_edge_3841_rejected(self):
        """Long edge must not exceed 3840."""
        with pytest.raises(ValueError, match="not exceed 3840"):
            resolve_size("3841x1024")

    def test_requested_pixels_exceeds_max_rejected(self):
        """Requested pixels > 8,294,400 rejected."""
        # 2881 * 2881 = 8,298,161 > 8,294,400
        with pytest.raises(ValueError, match="exceed 8,294,400"):
            resolve_size("2881x2881")

    def test_aspect_ratio_exceeds_3_to_1_rejected(self):
        """Aspect ratio > 3:1 rejected."""
        # 1024x3073 would be slightly over 3:1
        with pytest.raises(ValueError, match="3:1"):
            resolve_size("1024x3073")

    def test_upstream_canvas_rounding_overflow_rejected(self):
        """Requested size valid but upstream rounding causes pixel overflow.

        2576x3217: requested pixels = 8,287,192 < 8,294,400 (valid)
        But upstream after rounding to 16: 2576x3232 = 8,325,632 > 8,294,400 (invalid)
        """
        with pytest.raises(ValueError, match="valid gpt-image-2 canvas"):
            resolve_size("2576x3217")


class TestUpstreamConstraints:
    """Test all successful upstream dimensions meet constraints."""

    def test_upstream_width_is_16_multiple(self):
        result = resolve_size("1080x1920")
        upstream_w = int(result.upstream.split("x")[0])
        assert upstream_w % 16 == 0

    def test_upstream_height_is_16_multiple(self):
        result = resolve_size("1080x1920")
        upstream_h = int(result.upstream.split("x")[1])
        assert upstream_h % 16 == 0

    def test_upstream_short_edge_at_least_1024(self):
        result = resolve_size("256x512")
        upstream_w, upstream_h = map(int, result.upstream.split("x"))
        assert min(upstream_w, upstream_h) >= 1024

    def test_upstream_pixels_within_bounds(self):
        result = resolve_size("1080x1920")
        upstream_w, upstream_h = map(int, result.upstream.split("x"))
        pixels = upstream_w * upstream_h
        assert MIN_UPSTREAM_PIXELS <= pixels <= MAX_UPSTREAM_PIXELS


class TestIdempotence:
    """Test function has no global state, same input yields same output."""

    def test_repeated_calls_equal(self):
        result1 = resolve_size("1080x1920")
        result2 = resolve_size("1080x1920")
        assert result1 == result2

    def test_repeated_calls_different_inputs(self):
        result_a1 = resolve_size("1024x1024")
        result_b1 = resolve_size("1080x1920")
        result_a2 = resolve_size("1024x1024")
        result_b2 = resolve_size("1080x1920")
        assert result_a1 == result_a2
        assert result_b1 == result_b2


class TestIntegerUpstreamCalculation:
    """Verify upstream calculations use exact integer arithmetic, not floating point."""

    @pytest.mark.parametrize("requested,expected_upstream", [
        # short_edge < 1024: scale up to 1024 short edge
        ("256x257", "1024x1040"),  # ceil(Fraction(257*1024, 256)/16)*16 = ceil(1028/16)*16 = 65*16 = 1040
        ("257x256", "1040x1024"),  # ceil(Fraction(257*1024, 256)/16)*16 = 1040
        ("257x771", "1024x3072"),  # scale=1024/257≈3.9844, 771*1024/257=3072
        ("1023x3069", "1024x3072"), # scale=1024/1023≈1.00097, ceil each to 16-multiple
        # short_edge >= 1024: no scaling, just round to 16-multiple
        ("1024x3072", "1024x3072"), # already 16-aligned
        ("1080x1920", "1088x1920"), # 1080→1088, 1920 already aligned
        ("2880x2880", "2880x2880"), # already 16-aligned
    ])
    def test_upstream_exact_integer_oracle(self, requested, expected_upstream):
        """Verify upstream matches pure-integer calculation, no float precision issues."""
        result = resolve_size(requested)
        assert result.upstream == expected_upstream, (
            f"For {requested}: expected {expected_upstream}, got {result.upstream}"
        )

    def test_no_floating_point_in_aspect_check(self):
        """Aspect ratio check should use integer comparison: long > short * 3."""
        # 1024x3072 is exactly 3:1 (valid)
        resolve_size("1024x3072")
        # 1024x3073 is over 3:1 (invalid)
        with pytest.raises(ValueError, match="3:1"):
            resolve_size("1024x3073")
