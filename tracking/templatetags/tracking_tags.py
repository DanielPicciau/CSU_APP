"""
Custom template tags and filters for the tracking app.
"""

from django import template

register = template.Library()


@register.filter
def abs_value(value):
    """Return absolute value of a number."""
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value


@register.filter(name="abs")
def abs_filter(value):
    """Alias for abs_value."""
    return abs_value(value)


@register.filter
def score_color(score):
    """Return CSS variable for score color."""
    try:
        score = int(score)
        return f"var(--color-score-{score})"
    except (TypeError, ValueError):
        return "var(--text-primary)"


@register.filter
def percentage(value, max_value):
    """Calculate percentage of value relative to max."""
    try:
        return (float(value) / float(max_value)) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        return value - arg
    except (TypeError, ValueError):
        return value


@register.filter
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return value * arg
    except (TypeError, ValueError):
        return value
