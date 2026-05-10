"""KIE-model adapters.

Each adapter wraps a third-party model behind the
`paper3.data.kie_model_io.KIEModelInterface` so S5/S7/S8 can use it
without depending on any specific model.

Adapters are not auto-registered: importing this package alone does
nothing. To activate one, import the specific submodule, which calls
`register_kie_model_factory(...)` at import time.

    # Activate DONUT
    import paper3.adapters.donut

    # Then any model-aware script will pick it up:
    python -m paper3.scripts.s5_aad_overhead --corpus synthetic --n 200
"""
