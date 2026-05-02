"""Shared pytest fixtures and Hypothesis configuration."""

# Redirect Hypothesis example database into consolidated cache directory.
# Must be imported and called before any Hypothesis test collects/runs.
from hypothesis.configuration import set_hypothesis_home_dir

set_hypothesis_home_dir("../.cache/hypothesis")
