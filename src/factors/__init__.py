# src/factors/__init__.py
# Public exports for the factors package

from .effects import (
    estimate_main_effects,
    estimate_two_factor_cell_means,
    two_factor_interaction_matrix,
)
from .shap_fit import (
    compute_shap_explainer_values,
    fit_two_factor_approx_from_shap,
)

__all__ = [
    "estimate_main_effects",
    "estimate_two_factor_cell_means",
    "two_factor_interaction_matrix",
    "compute_shap_explainer_values",
    "fit_two_factor_approx_from_shap",
]
