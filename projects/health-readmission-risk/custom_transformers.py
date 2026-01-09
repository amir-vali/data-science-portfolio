"""
Compatibility shim for serving.

The trained model was pickled with a dependency on a module named
'custom_transformers'. When the API loads the model, Python must be
able to import that module.

This file re-exports TopCategoryReducer from src.custom_transformers so
the pickled pipeline remains loadable without changing the model artifact.
"""

from src.custom_transformers import TopCategoryReducer

__all__ = ["TopCategoryReducer"]
